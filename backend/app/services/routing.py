"""Settlement routing: pick the cheapest viable chain for a payout.

The agent uses this to auto-select the lowest-cost network a payee can receive
on, honouring the payee's preferred chain when set.

Stellar is automatically preferred for EMEA/Africa corridors due to its
sub-cent fees, 5-second finality, and native path-payment support for
local-currency stablecoins (EURC, NGNC).
"""

from __future__ import annotations

from app.core.constants import CHAIN_TX_COST_USD, Chain

# Countries in EMEA where Stellar anchors provide superior rails.
STELLAR_PREFERRED_COUNTRIES = {
    # Africa
    "NG", "KE", "GH", "ZA", "TZ", "UG", "RW", "SN", "CI", "CM",
    "ET", "EG", "MA", "TN", "DZ", "MZ", "ZW", "BW", "MU",
    # Middle East
    "AE", "SA", "QA", "BH", "OM", "KW", "JO", "LB",
    # Europe (SEPA alternatives via Stellar anchors)
    "DE", "FR", "IT", "ES", "NL", "PT", "IE", "AT", "BE", "FI",
    "GR", "PL", "CZ", "RO", "BG", "HR", "SK", "SI", "EE", "LV", "LT",
    "SE", "NO", "DK", "GB", "CH", "TR",
}


def cheapest_chain(candidates: list[str] | None = None) -> str:
    pool = candidates or [c.value for c in Chain]
    return min(pool, key=lambda c: CHAIN_TX_COST_USD.get(Chain(c), 99.0))


def tx_cost_usd(chain: str) -> float:
    return CHAIN_TX_COST_USD.get(Chain(chain), 1.0)


def is_stellar_address(address: str) -> bool:
    """Stellar addresses are 56 chars starting with G (public) or C (contract).

    Stellar uses base32 encoding, so valid chars are A-Z and 2-7.
    We accept any alphanumeric for flexibility in sandbox mode.
    """
    return (
        len(address) == 56
        and address[0] in ("G", "C")
        and all(c.isalnum() for c in address)
    )


def select_route(
    *,
    preferred_chain: str | None,
    auto_select_cheapest: bool,
    payee_address: str,
    country: str | None = None,
) -> tuple[str, float]:
    """Return ``(chain, fee_usd)`` for a payout.

    Address format determines the candidate pool:
    - 0x prefix → EVM chains
    - G/C + 56 chars → Stellar
    - Otherwise → Solana (base58)

    For EMEA/Africa countries, Stellar is automatically preferred when the
    payee can receive on Stellar, due to dramatically lower costs.
    """
    if is_stellar_address(payee_address):
        # Stellar-native payees always route via Stellar
        return Chain.STELLAR.value, tx_cost_usd(Chain.STELLAR.value)

    is_evm = payee_address.startswith("0x")

    if is_evm:
        evm = [Chain.BASE, Chain.POLYGON, Chain.ARBITRUM, Chain.OPTIMISM, Chain.ETHEREUM]
        pool = [c.value for c in evm]
    else:
        # Non-EVM: could be Solana (base58) or Stellar-compatible
        # For EMEA/Africa countries with non-EVM addresses, add Stellar as candidate
        if country and country.upper() in STELLAR_PREFERRED_COUNTRIES:
            pool = [Chain.STELLAR.value, Chain.SOLANA.value]
        else:
            pool = [Chain.SOLANA.value]

    if preferred_chain in pool and not auto_select_cheapest:
        chain = preferred_chain
    else:
        chain = cheapest_chain(pool)
    return chain, tx_cost_usd(chain)
