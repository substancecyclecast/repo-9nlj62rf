//! Mandate Treasury Policy Contract (Soroban)
//!
//! Enforces on-chain spending limits, compliance allowlists, and time-locked
//! withdrawals for the Mandate autonomous CFO agent.
//!
//! # Features
//! - Per-transaction spending limit (default: $25,000 equivalent)
//! - Daily aggregate spending cap (default: $100,000 equivalent)
//! - Address allowlist (only pre-approved recipients)
//! - Time-locked withdrawals (24h hold for amounts > $100,000)
//! - Admin management (add/remove allowed addresses, update limits)
//!
//! # Architecture
//! This contract is invoked by the Mandate agent before executing any
//! treasury operation. If the policy check fails, the transaction is
//! rejected at the smart contract level — providing cryptographic
//! guarantees beyond application-level policy enforcement.

#![no_std]

use soroban_sdk::{
    contract, contractimpl, contracttype, Address, Env, Vec,
};

/// Storage keys for persistent contract state.
#[derive(Clone)]
#[contracttype]
pub enum DataKey {
    Admin,             // Address: contract administrator
    SingleLimit,       // i128: max per-transaction amount (in stroops/base units)
    DailyLimit,        // i128: max daily aggregate
    DailySpend,        // i128: current day's aggregate spend
    DayTimestamp,      // u64: start of current day (unix timestamp)
    TimelockThreshold, // i128: amount above which 24h timelock applies
    Allowlist,         // Vec<Address>: approved recipient addresses
    NextPendingId,     // u64: auto-incrementing counter for pending transfer IDs
    Pending(u64),      // PendingTx stored per-id
}

/// A pending time-locked transfer awaiting execution.
#[derive(Clone)]
#[contracttype]
pub struct PendingTx {
    pub id: u64,
    pub recipient: Address,
    pub amount: i128,
    pub asset: Address,
    pub unlock_at: u64, // Unix timestamp when transfer can execute
    pub proposer: Address,
}

/// Result of a policy check.
#[derive(Clone)]
#[contracttype]
pub struct PolicyResult {
    pub allowed: bool,
    pub requires_timelock: bool,
    pub reason: u32, // 0=ok, 1=over_single, 2=over_daily, 3=not_in_allowlist, 4=timelocked
}

/// Result of a queue operation.
#[derive(Clone)]
#[contracttype]
pub struct QueueResult {
    pub queued: bool,
    pub pending_id: u64,
    pub unlock_at: u64,
}

#[contract]
pub struct MandatePolicy;

const TIMELOCK_DURATION: u64 = 86400; // 24 hours in seconds

#[contractimpl]
impl MandatePolicy {
    /// Initialize the contract with admin and default limits.
    pub fn initialize(
        env: Env,
        admin: Address,
        single_limit: i128,
        daily_limit: i128,
        timelock_threshold: i128,
    ) {
        admin.require_auth();

        env.storage().persistent().set(&DataKey::Admin, &admin);
        env.storage().persistent().set(&DataKey::SingleLimit, &single_limit);
        env.storage().persistent().set(&DataKey::DailyLimit, &daily_limit);
        env.storage().persistent().set(&DataKey::TimelockThreshold, &timelock_threshold);
        env.storage().persistent().set(&DataKey::DailySpend, &0i128);
        env.storage().persistent().set(&DataKey::DayTimestamp, &env.ledger().timestamp());
        env.storage().persistent().set(&DataKey::NextPendingId, &0u64);

        let empty_list: Vec<Address> = Vec::new(&env);
        env.storage().persistent().set(&DataKey::Allowlist, &empty_list);
    }

    /// Check if a transfer is allowed by the current policy.
    /// Does NOT modify state — use `approve_transfer` to actually record spend.
    pub fn check_transfer(
        env: Env,
        recipient: Address,
        amount: i128,
    ) -> PolicyResult {
        // Check 1: Single transaction limit
        let single_limit: i128 = env.storage().persistent().get(&DataKey::SingleLimit).unwrap_or(25_000_000_000); // 25k * 10^6
        if amount > single_limit {
            return PolicyResult {
                allowed: false,
                requires_timelock: false,
                reason: 1,
            };
        }

        // Check 2: Daily aggregate limit
        Self::maybe_reset_daily(&env);
        let daily_spend: i128 = env.storage().persistent().get(&DataKey::DailySpend).unwrap_or(0);
        let daily_limit: i128 = env.storage().persistent().get(&DataKey::DailyLimit).unwrap_or(100_000_000_000);
        if daily_spend + amount > daily_limit {
            return PolicyResult {
                allowed: false,
                requires_timelock: false,
                reason: 2,
            };
        }

        // Check 3: Allowlist
        let allowlist: Vec<Address> = env.storage().persistent().get(&DataKey::Allowlist).unwrap_or(Vec::new(&env));
        if allowlist.len() > 0 {
            let mut found = false;
            for i in 0..allowlist.len() {
                if allowlist.get(i).unwrap() == recipient {
                    found = true;
                    break;
                }
            }
            if !found {
                return PolicyResult {
                    allowed: false,
                    requires_timelock: false,
                    reason: 3,
                };
            }
        }

        // Check 4: Timelock threshold
        let timelock_threshold: i128 = env.storage().persistent().get(&DataKey::TimelockThreshold).unwrap_or(100_000_000_000);
        if amount > timelock_threshold {
            return PolicyResult {
                allowed: true,
                requires_timelock: true,
                reason: 4,
            };
        }

        PolicyResult {
            allowed: true,
            requires_timelock: false,
            reason: 0,
        }
    }

    /// Approve a transfer and record the spend against daily limits.
    /// If the amount exceeds the timelock threshold, the transfer must be
    /// queued via `queue_transfer` instead.
    pub fn approve_transfer(
        env: Env,
        caller: Address,
        recipient: Address,
        amount: i128,
    ) -> PolicyResult {
        caller.require_auth();

        let result = Self::check_transfer(env.clone(), recipient, amount);
        if !result.allowed {
            return result;
        }

        // If timelock is required, block direct approval
        if result.requires_timelock {
            return PolicyResult {
                allowed: false,
                requires_timelock: true,
                reason: 4,
            };
        }

        // Record spend
        Self::maybe_reset_daily(&env);
        let daily_spend: i128 = env.storage().persistent().get(&DataKey::DailySpend).unwrap_or(0);
        env.storage().persistent().set(&DataKey::DailySpend, &(daily_spend + amount));

        result
    }

    // --- Timelock functions ---

    /// Queue a transfer for time-locked execution. Required for amounts above
    /// the timelock threshold. The transfer can be executed after `unlock_at`
    /// (current timestamp + 24 hours).
    pub fn queue_transfer(
        env: Env,
        proposer: Address,
        recipient: Address,
        amount: i128,
        asset: Address,
    ) -> QueueResult {
        proposer.require_auth();

        // Validate: must be above timelock threshold to require queuing
        let timelock_threshold: i128 = env.storage().persistent().get(&DataKey::TimelockThreshold).unwrap_or(100_000_000_000);
        if amount <= timelock_threshold {
            panic!("amount below timelock threshold; use approve_transfer instead");
        }

        // Basic policy checks (daily limit, allowlist) still apply
        let check = Self::check_transfer(env.clone(), recipient.clone(), amount);
        if !check.allowed {
            panic!("transfer not allowed by policy");
        }

        let next_id: u64 = env.storage().persistent().get(&DataKey::NextPendingId).unwrap_or(0);
        let unlock_at = env.ledger().timestamp() + TIMELOCK_DURATION;

        let pending = PendingTx {
            id: next_id,
            recipient,
            amount,
            asset,
            unlock_at,
            proposer,
        };

        env.storage().persistent().set(&DataKey::Pending(next_id), &pending);
        env.storage().persistent().set(&DataKey::NextPendingId, &(next_id + 1));

        QueueResult {
            queued: true,
            pending_id: next_id,
            unlock_at,
        }
    }

    /// Execute a pending time-locked transfer after the unlock period.
    /// Records the spend against daily limits.
    pub fn execute_pending(env: Env, caller: Address, pending_id: u64) -> PolicyResult {
        caller.require_auth();

        let pending: PendingTx = env
            .storage()
            .persistent()
            .get(&DataKey::Pending(pending_id))
            .unwrap_or_else(|| panic!("pending transfer not found"));

        // Check timelock has elapsed
        let now = env.ledger().timestamp();
        if now < pending.unlock_at {
            panic!("timelock not elapsed");
        }

        // Check daily limit still allows it
        Self::maybe_reset_daily(&env);
        let daily_spend: i128 = env.storage().persistent().get(&DataKey::DailySpend).unwrap_or(0);
        let daily_limit: i128 = env.storage().persistent().get(&DataKey::DailyLimit).unwrap_or(100_000_000_000);
        if daily_spend + pending.amount > daily_limit {
            return PolicyResult {
                allowed: false,
                requires_timelock: false,
                reason: 2,
            };
        }

        // Record spend and remove pending
        env.storage().persistent().set(&DataKey::DailySpend, &(daily_spend + pending.amount));
        env.storage().persistent().remove(&DataKey::Pending(pending_id));

        PolicyResult {
            allowed: true,
            requires_timelock: false,
            reason: 0,
        }
    }

    /// Cancel a pending time-locked transfer. Only admin can cancel.
    pub fn cancel_pending(env: Env, admin: Address, pending_id: u64) {
        admin.require_auth();
        Self::require_admin(&env, &admin);

        if !env.storage().persistent().has(&DataKey::Pending(pending_id)) {
            panic!("pending transfer not found");
        }

        env.storage().persistent().remove(&DataKey::Pending(pending_id));
    }

    /// Get details of a pending transfer.
    pub fn get_pending(env: Env, pending_id: u64) -> PendingTx {
        env.storage()
            .persistent()
            .get(&DataKey::Pending(pending_id))
            .unwrap_or_else(|| panic!("pending transfer not found"))
    }

    // --- Admin functions ---

    /// Add an address to the allowlist.
    pub fn add_to_allowlist(env: Env, admin: Address, address: Address) {
        admin.require_auth();
        Self::require_admin(&env, &admin);

        let mut allowlist: Vec<Address> = env.storage().persistent().get(&DataKey::Allowlist).unwrap_or(Vec::new(&env));
        allowlist.push_back(address);
        env.storage().persistent().set(&DataKey::Allowlist, &allowlist);
    }

    /// Remove an address from the allowlist.
    pub fn remove_from_allowlist(env: Env, admin: Address, index: u32) {
        admin.require_auth();
        Self::require_admin(&env, &admin);

        let mut allowlist: Vec<Address> = env.storage().persistent().get(&DataKey::Allowlist).unwrap_or(Vec::new(&env));
        allowlist.remove(index);
        env.storage().persistent().set(&DataKey::Allowlist, &allowlist);
    }

    /// Update spending limits.
    pub fn update_limits(
        env: Env,
        admin: Address,
        single_limit: i128,
        daily_limit: i128,
        timelock_threshold: i128,
    ) {
        admin.require_auth();
        Self::require_admin(&env, &admin);

        env.storage().persistent().set(&DataKey::SingleLimit, &single_limit);
        env.storage().persistent().set(&DataKey::DailyLimit, &daily_limit);
        env.storage().persistent().set(&DataKey::TimelockThreshold, &timelock_threshold);
    }

    /// Get current contract state for inspection.
    pub fn get_state(env: Env) -> (i128, i128, i128, i128, u32) {
        let single_limit: i128 = env.storage().persistent().get(&DataKey::SingleLimit).unwrap_or(0);
        let daily_limit: i128 = env.storage().persistent().get(&DataKey::DailyLimit).unwrap_or(0);
        let daily_spend: i128 = env.storage().persistent().get(&DataKey::DailySpend).unwrap_or(0);
        let timelock: i128 = env.storage().persistent().get(&DataKey::TimelockThreshold).unwrap_or(0);
        let allowlist: Vec<Address> = env.storage().persistent().get(&DataKey::Allowlist).unwrap_or(Vec::new(&env));
        (single_limit, daily_limit, daily_spend, timelock, allowlist.len())
    }

    // --- Internal helpers ---

    fn maybe_reset_daily(env: &Env) {
        let day_ts: u64 = env.storage().persistent().get(&DataKey::DayTimestamp).unwrap_or(0);
        let current = env.ledger().timestamp();
        // Reset every 86400 seconds (24 hours)
        if current - day_ts >= 86400 {
            env.storage().persistent().set(&DataKey::DailySpend, &0i128);
            env.storage().persistent().set(&DataKey::DayTimestamp, &current);
        }
    }

    fn require_admin(env: &Env, caller: &Address) {
        let admin: Address = env.storage().persistent().get(&DataKey::Admin).unwrap();
        if *caller != admin {
            panic!("not admin");
        }
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use soroban_sdk::testutils::Address as _;
    use soroban_sdk::testutils::Ledger;
    use soroban_sdk::Env;

    #[test]
    fn test_initialize_and_check() {
        let env = Env::default();
        let contract_id = env.register_contract(None, MandatePolicy);
        let client = MandatePolicyClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        let recipient = Address::generate(&env);

        env.mock_all_auths();

        // Initialize: $25k single, $100k daily, $100k timelock
        client.initialize(&admin, &25_000_000_000, &100_000_000_000, &100_000_000_000);

        // Small transfer: should pass
        let result = client.check_transfer(&recipient, &10_000_000_000); // $10k
        assert!(result.allowed);
        assert!(!result.requires_timelock);
        assert_eq!(result.reason, 0);

        // Over single limit: should fail
        let result = client.check_transfer(&recipient, &30_000_000_000); // $30k
        assert!(!result.allowed);
        assert_eq!(result.reason, 1);
    }

    #[test]
    fn test_daily_limit() {
        let env = Env::default();
        let contract_id = env.register_contract(None, MandatePolicy);
        let client = MandatePolicyClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        let caller = Address::generate(&env);
        let recipient = Address::generate(&env);

        env.mock_all_auths();

        client.initialize(&admin, &25_000_000_000, &50_000_000_000, &100_000_000_000);

        // First transfer: $20k — should pass
        let r1 = client.approve_transfer(&caller, &recipient, &20_000_000_000);
        assert!(r1.allowed);

        // Second transfer: $20k — should pass (total $40k < $50k daily)
        let r2 = client.approve_transfer(&caller, &recipient, &20_000_000_000);
        assert!(r2.allowed);

        // Third transfer: $20k — should fail (total $60k > $50k daily)
        let r3 = client.check_transfer(&recipient, &20_000_000_000);
        assert!(!r3.allowed);
        assert_eq!(r3.reason, 2);
    }

    #[test]
    fn test_allowlist() {
        let env = Env::default();
        let contract_id = env.register_contract(None, MandatePolicy);
        let client = MandatePolicyClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        let allowed = Address::generate(&env);
        let blocked = Address::generate(&env);

        env.mock_all_auths();

        client.initialize(&admin, &25_000_000_000, &100_000_000_000, &100_000_000_000);
        client.add_to_allowlist(&admin, &allowed);

        // Allowed address: should pass
        let r1 = client.check_transfer(&allowed, &1_000_000_000);
        assert!(r1.allowed);

        // Blocked address: should fail
        let r2 = client.check_transfer(&blocked, &1_000_000_000);
        assert!(!r2.allowed);
        assert_eq!(r2.reason, 3);
    }

    #[test]
    fn test_timelock_queue_and_early_execute_fails() {
        let env = Env::default();
        let contract_id = env.register_contract(None, MandatePolicy);
        let client = MandatePolicyClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        let proposer = Address::generate(&env);
        let recipient = Address::generate(&env);
        let asset = Address::generate(&env);

        env.mock_all_auths();

        // single_limit high (200k), daily high (500k), timelock at 100k
        client.initialize(&admin, &200_000_000_000, &500_000_000_000, &100_000_000_000);

        // Transfer > timelock threshold requires queuing
        let check = client.check_transfer(&recipient, &150_000_000_000);
        assert!(check.allowed);
        assert!(check.requires_timelock);
        assert_eq!(check.reason, 4);

        // approve_transfer should block for timelocked amounts
        let approve = client.approve_transfer(&proposer, &recipient, &150_000_000_000);
        assert!(!approve.allowed);
        assert!(approve.requires_timelock);

        // Queue the transfer
        let queue_result = client.queue_transfer(
            &proposer,
            &recipient,
            &150_000_000_000,
            &asset,
        );
        assert!(queue_result.queued);
        assert_eq!(queue_result.pending_id, 0);

        // Verify pending transfer exists
        let pending = client.get_pending(&0);
        assert_eq!(pending.amount, 150_000_000_000);

        // Try to execute early — should panic
        let early_execute = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            client.execute_pending(&proposer, &0);
        }));
        assert!(early_execute.is_err(), "early execute should panic");
    }

    #[test]
    fn test_timelock_execute_after_delay() {
        let env = Env::default();
        let contract_id = env.register_contract(None, MandatePolicy);
        let client = MandatePolicyClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        let proposer = Address::generate(&env);
        let recipient = Address::generate(&env);
        let asset = Address::generate(&env);

        env.mock_all_auths();

        let initial_ts = 1_000_000u64;
        env.ledger().set_timestamp(initial_ts);

        // single_limit high, daily high, timelock at 100k
        client.initialize(&admin, &200_000_000_000, &500_000_000_000, &100_000_000_000);

        // Queue a transfer above timelock threshold
        let queue_result = client.queue_transfer(
            &proposer,
            &recipient,
            &150_000_000_000,
            &asset,
        );
        assert!(queue_result.queued);
        assert_eq!(queue_result.unlock_at, initial_ts + 86400);

        // Advance time past the timelock period
        env.ledger().set_timestamp(initial_ts + 86400 + 1);

        // Now execute should succeed
        let exec_result = client.execute_pending(&proposer, &queue_result.pending_id);
        assert!(exec_result.allowed);
        assert_eq!(exec_result.reason, 0);

        // Pending transfer should be removed — trying to get it should panic
        let get_removed = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            client.get_pending(&queue_result.pending_id);
        }));
        assert!(get_removed.is_err(), "pending should be removed after execution");
    }

    #[test]
    fn test_timelock_cancel() {
        let env = Env::default();
        let contract_id = env.register_contract(None, MandatePolicy);
        let client = MandatePolicyClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        let proposer = Address::generate(&env);
        let recipient = Address::generate(&env);
        let asset = Address::generate(&env);

        env.mock_all_auths();

        client.initialize(&admin, &200_000_000_000, &500_000_000_000, &100_000_000_000);

        // Queue a transfer
        let queue_result = client.queue_transfer(
            &proposer,
            &recipient,
            &150_000_000_000,
            &asset,
        );
        assert!(queue_result.queued);

        // Admin cancels
        client.cancel_pending(&admin, &queue_result.pending_id);

        // Trying to get it should panic
        let get_cancelled = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            client.get_pending(&queue_result.pending_id);
        }));
        assert!(get_cancelled.is_err(), "cancelled pending should not exist");
    }

    #[test]
    fn test_timelock_multiple_pending() {
        let env = Env::default();
        let contract_id = env.register_contract(None, MandatePolicy);
        let client = MandatePolicyClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        let proposer = Address::generate(&env);
        let recipient1 = Address::generate(&env);
        let recipient2 = Address::generate(&env);
        let asset = Address::generate(&env);

        env.mock_all_auths();

        client.initialize(&admin, &200_000_000_000, &500_000_000_000, &100_000_000_000);

        // Queue two transfers
        let q1 = client.queue_transfer(&proposer, &recipient1, &150_000_000_000, &asset);
        let q2 = client.queue_transfer(&proposer, &recipient2, &120_000_000_000, &asset);

        assert_eq!(q1.pending_id, 0);
        assert_eq!(q2.pending_id, 1);

        // Both should exist
        let p1 = client.get_pending(&0);
        assert_eq!(p1.amount, 150_000_000_000);
        let p2 = client.get_pending(&1);
        assert_eq!(p2.amount, 120_000_000_000);
    }
}
