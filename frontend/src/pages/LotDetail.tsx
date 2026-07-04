import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import api, { apiErrorDetail } from '../api/client';
import { CheckCircle, XCircle, Clock, AlertTriangle, ChevronDown, type LucideIcon } from 'lucide-react';

interface SupplierOffer {
  // поддержка разных схем: live-отчёт / seed-фикстура / фронт
  supplier?: string;
  supplier_name?: string;
  name?: string;
  inn?: string;
  total_price?: number | string;
  total_price_rub?: number | string;
  price_rub?: number | string;
  lead_time_days?: number;
  delivery_days?: number;
  score?: number;
  recommendation?: string;
  supplier_id?: string;
}

interface FinalReport {
  top_3?: SupplierOffer[];
  top_suppliers?: SupplierOffer[];
  savings_pct?: number;
  savings_vs_avg_pct?: number;
  savings_rub?: number;
  savings_vs_avg_rub?: number;
  nmck_justification?: string;
  summary?: string;
  [key: string]: unknown;
}

function offerName(s: SupplierOffer): string {
  return s.supplier_name || s.supplier || s.name || 'Поставщик';
}

function offerPrice(s: SupplierOffer): number | undefined {
  const v = s.total_price_rub ?? s.total_price ?? s.price_rub;
  return v === undefined || v === null ? undefined : Number(v);
}

interface LotData {
  id: string;
  status: string;
  phase: string | null;
  category: string | null;
  raw_request: string;
  parsed_items: Record<string, unknown>[];
  final_report: FinalReport | null;
  requires_human: boolean;
  escalation_reason: string | null;
  created_at: string;
  updated_at: string;
}

interface AuditEntry {
  id: string;
  agent: string;
  action: string;
  details: unknown;
  created_at: string;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: LucideIcon }> = {
  draft: { label: 'Черновик', color: 'bg-gray-100 text-gray-700', icon: Clock },
  planned: { label: 'Запланирован', color: 'bg-blue-100 text-blue-700', icon: Clock },
  sourcing: { label: 'Поиск поставщиков', color: 'bg-yellow-100 text-yellow-700', icon: Clock },
  rfq_sent: { label: 'Запросы отправлены', color: 'bg-orange-100 text-orange-700', icon: Clock },
  responses_collected: { label: 'Ответы собраны', color: 'bg-indigo-100 text-indigo-700', icon: Clock },
  negotiating: { label: 'Переговоры', color: 'bg-purple-100 text-purple-700', icon: Clock },
  verified: { label: 'Проверено', color: 'bg-teal-100 text-teal-700', icon: CheckCircle },
  report_ready: { label: 'Отчёт готов', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  approved: { label: 'Одобрен', color: 'bg-green-200 text-green-800', icon: CheckCircle },
  rejected: { label: 'Отклонён', color: 'bg-red-100 text-red-700', icon: XCircle },
  escalated: { label: 'Эскалирован', color: 'bg-red-200 text-red-800', icon: AlertTriangle },
  failed: { label: 'Ошибка', color: 'bg-red-300 text-red-900', icon: XCircle },
};

const PIPELINE_STEPS = ['draft', 'planned', 'sourcing', 'rfq_sent', 'responses_collected', 'negotiating', 'verified', 'report_ready', 'approved'];

export default function LotDetail() {
  const { id } = useParams<{ id: string }>();
  const [lot, setLot] = useState<LotData | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAudit, setShowAudit] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    Promise.all([
      api.get(`/lots/${id}`),
      api.get(`/lots/${id}/audit`).catch(() => ({ data: [] })),
    ])
      .then(([lotResp, auditResp]) => {
        setLot(lotResp.data);
        setAudit(auditResp.data);
      })
      .catch(() => setError('Лот не найден'))
      .finally(() => setLoading(false));
  }, [id]);

  const handleApprove = async (supplierId?: string) => {
    if (!id) return;
    try {
      await api.post(`/lots/${id}/approve`, { supplier_id: supplierId });
      const resp = await api.get(`/lots/${id}`);
      setLot(resp.data);
    } catch (err) {
      setError(apiErrorDetail(err, 'Ошибка'));
    }
  };

  if (loading) return <div className="text-center py-12 text-gray-500">Загрузка...</div>;
  if (error || !lot) return <div className="text-center py-12 text-red-500">{error || 'Ошибка'}</div>;

  const statusCfg = STATUS_CONFIG[lot.status] || { label: lot.status, color: 'bg-gray-100 text-gray-700', icon: Clock };
  const StatusIcon = statusCfg.icon;
  const currentStep = PIPELINE_STEPS.indexOf(lot.status);
  const report = lot.final_report;
  const top3: SupplierOffer[] = report?.top_3 || report?.top_suppliers || [];
  const savings = report?.savings_pct ?? report?.savings_vs_avg_pct;

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            Лот <span className="font-mono text-lg">{lot.id.slice(0, 8)}…</span>
          </h1>
          <div className="flex items-center gap-3 mt-2">
            <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${statusCfg.color}`}>
              <StatusIcon className="w-3.5 h-3.5" /> {statusCfg.label}
            </span>
            {lot.category && <span className="text-sm text-gray-500">{lot.category}</span>}
            {lot.phase && <span className="text-sm text-gray-400">Фаза: {lot.phase}</span>}
          </div>
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Создан: {new Date(lot.created_at).toLocaleString('ru-RU')}
        </div>
      </div>

      {/* Progress stepper */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-4 mb-6 border border-gray-100 dark:border-gray-700 overflow-x-auto">
        <div className="flex items-center min-w-max">
          {PIPELINE_STEPS.map((_step, i) => {
            const done = i <= currentStep;
            return (
              <div key={_step} className="flex items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${done ? 'bg-primary text-white' : 'bg-gray-200 dark:bg-gray-600 text-gray-500 dark:text-gray-400'}`}>
                  {i + 1}
                </div>
                {i < PIPELINE_STEPS.length - 1 && (
                  <div className={`w-8 h-0.5 ${done && i < currentStep ? 'bg-primary' : 'bg-gray-200 dark:bg-gray-600'}`} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Description */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 mb-6 border border-gray-100 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Описание заявки</h2>
        <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{lot.raw_request}</p>
      </div>

      {/* Top-3 suppliers */}
      {top3.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 mb-6 border border-gray-100 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Топ-3 поставщика</h2>
          <div className="space-y-3">
            {top3.map((s, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-sm">{i + 1}</span>
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">{offerName(s)}</div>
                    {s.inn && <div className="text-xs text-gray-500">ИНН: {s.inn}</div>}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-gray-900 dark:text-white">
                    {offerPrice(s) !== undefined ? `${offerPrice(s)!.toLocaleString('ru-RU')} ₽` : '—'}
                  </div>
                  {(s.lead_time_days ?? s.delivery_days) !== undefined && (
                    <div className="text-xs text-gray-500">Срок: {s.lead_time_days ?? s.delivery_days} дн.</div>
                  )}
                </div>
              </div>
            ))}
          </div>
          {savings !== undefined && savings > 0 && (
            <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg text-green-700 dark:text-green-400 text-sm">
              Экономия: {savings}%
            </div>
          )}
          {lot.status === 'report_ready' && (
            <div className="mt-4 flex gap-2">
              <button onClick={() => handleApprove(top3[0]?.supplier_id)} className="bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-dark transition text-sm">
                Одобрить
              </button>
            </div>
          )}
        </div>
      )}

      {/* Escalation */}
      {lot.escalation_reason && (
        <div className="bg-red-50 dark:bg-red-900/20 rounded-xl p-4 mb-6 border border-red-200 dark:border-red-800">
          <h3 className="font-semibold text-red-800 dark:text-red-300 mb-1">Требуется внимание</h3>
          <p className="text-red-700 dark:text-red-400 text-sm">{lot.escalation_reason}</p>
        </div>
      )}

      {/* Audit log */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
        <button onClick={() => setShowAudit(!showAudit)} className="w-full p-4 flex items-center justify-between text-left">
          <h2 className="font-semibold text-gray-900 dark:text-white">Audit log ({audit.length})</h2>
          <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${showAudit ? 'rotate-180' : ''}`} />
        </button>
        {showAudit && (
          <div className="border-t border-gray-100 dark:border-gray-700 max-h-96 overflow-y-auto">
            {audit.length === 0 ? (
              <div className="p-4 text-gray-500 text-sm">Нет записей</div>
            ) : (
              <div className="divide-y divide-gray-100 dark:divide-gray-700">
                {audit.map((entry) => (
                  <div key={entry.id} className="p-3 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-primary">{entry.agent}</span>
                      <span className="text-gray-500">→</span>
                      <span className="text-gray-700 dark:text-gray-300">{entry.action}</span>
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {new Date(entry.created_at).toLocaleString('ru-RU')}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
