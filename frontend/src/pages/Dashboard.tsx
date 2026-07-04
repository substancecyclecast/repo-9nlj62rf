import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { Package, CheckCircle, Clock, AlertTriangle } from 'lucide-react';

interface Lot {
  id: string;
  status: string;
  category: string | null;
  raw_request_preview: string;
  created_at: string;
  requires_human: boolean;
}

interface Stats {
  processing: number;
  ready: number;
  approved: number;
  total: number;
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  planned: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  sourcing: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  rfq_sent: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  responses_collected: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  negotiating: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  verified: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
  report_ready: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  approved: 'bg-green-200 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  escalated: 'bg-red-200 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  failed: 'bg-red-300 text-red-900 dark:bg-red-900/50 dark:text-red-200',
};

const STATUS_LABELS: Record<string, string> = {
  draft: 'Черновик', planned: 'Запланирован', sourcing: 'Поиск',
  rfq_sent: 'Запросы отправлены', responses_collected: 'Ответы собраны',
  negotiating: 'Переговоры', verified: 'Проверено', report_ready: 'Отчёт готов',
  approved: 'Одобрен', rejected: 'Отклонён', escalated: 'Эскалирован', failed: 'Ошибка',
};

export default function Dashboard() {
  const [lots, setLots] = useState<Lot[]>([]);
  const [stats, setStats] = useState<Stats>({ processing: 0, ready: 0, approved: 0, total: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/lots', { params: { page_size: 10 } })
      .then((r) => {
        const items = r.data.items || [];
        setLots(items);
        const processing = items.filter((l: Lot) => ['sourcing', 'rfq_sent', 'negotiating', 'planned'].includes(l.status)).length;
        const ready = items.filter((l: Lot) => ['report_ready', 'verified'].includes(l.status)).length;
        const approved = items.filter((l: Lot) => l.status === 'approved').length;
        setStats({ processing, ready, approved, total: r.data.total || items.length });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const KPI = [
    { label: 'В обработке', value: stats.processing, icon: Clock, color: 'text-yellow-600' },
    { label: 'Готовы', value: stats.ready, icon: Package, color: 'text-blue-600' },
    { label: 'Одобрено', value: stats.approved, icon: CheckCircle, color: 'text-green-600' },
    { label: 'Всего лотов', value: stats.total, icon: AlertTriangle, color: 'text-gray-600' },
  ];

  if (loading) return <div className="text-center py-12 text-gray-500">Загрузка...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Панель управления</h1>

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {KPI.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-3 min-w-0">
              <Icon className={`w-8 h-8 shrink-0 ${color}`} />
              <div className="min-w-0">
                <div className="text-2xl font-bold text-gray-900 dark:text-white truncate">{value}</div>
                <div className="text-xs text-gray-500 dark:text-gray-400 truncate">{label}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Lots table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
        <div className="p-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900 dark:text-white">Последние лоты</h2>
          <Link to="/lots/new" className="text-sm bg-primary text-white px-3 py-1.5 rounded-lg hover:bg-primary-dark transition">
            + Новый лот
          </Link>
        </div>
        {lots.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            Лотов пока нет. <Link to="/lots/new" className="text-primary hover:underline">Создать первый лот</Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-4 py-2 text-left text-gray-600 dark:text-gray-300">ID</th>
                  <th className="px-4 py-2 text-left text-gray-600 dark:text-gray-300">Описание</th>
                  <th className="px-4 py-2 text-left text-gray-600 dark:text-gray-300">Статус</th>
                  <th className="px-4 py-2 text-left text-gray-600 dark:text-gray-300">Категория</th>
                  <th className="px-4 py-2 text-left text-gray-600 dark:text-gray-300">Дата</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {lots.map((lot) => (
                  <tr key={lot.id} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                    <td className="px-4 py-3">
                      <Link to={`/lots/${lot.id}`} className="text-primary hover:underline font-mono text-xs">
                        {lot.id.slice(0, 8)}…
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-700 dark:text-gray-300 max-w-[200px] truncate">{lot.raw_request_preview}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[lot.status] || 'bg-gray-100 text-gray-700'}`}>
                        {STATUS_LABELS[lot.status] || lot.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{lot.category || '—'}</td>
                    <td className="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs">
                      {new Date(lot.created_at).toLocaleDateString('ru-RU')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
