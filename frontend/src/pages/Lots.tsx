import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';

interface Lot {
  id: string;
  status: string;
  category: string | null;
  raw_request_preview: string;
  created_at: string;
  requires_human: boolean;
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Черновик', planned: 'Запланирован', sourcing: 'Поиск',
  rfq_sent: 'Запросы отправлены', responses_collected: 'Ответы собраны',
  negotiating: 'Переговоры', verified: 'Проверено', report_ready: 'Отчёт готов',
  approved: 'Одобрен', rejected: 'Отклонён', escalated: 'Эскалирован', failed: 'Ошибка',
};

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  approved: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  report_ready: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  escalated: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

export default function Lots() {
  const [lots, setLots] = useState<Lot[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const pageSize = 20;

  useEffect(() => {
    setLoading(true);
    const params: Record<string, string | number> = { page, page_size: pageSize };
    if (statusFilter) params.status = statusFilter;
    api.get('/lots', { params })
      .then((r) => {
        setLots(r.data.items || []);
        setTotal(r.data.total || 0);
        setPages(r.data.pages || 1);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page, statusFilter]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Лоты</h1>
        <Link to="/lots/new" className="bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-dark transition text-sm">
          + Новый лот
        </Link>
      </div>

      {/* Filter */}
      <div className="mb-4">
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm">
          <option value="">Все статусы</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <span className="ml-3 text-sm text-gray-500">Найдено: {total}</span>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Загрузка...</div>
      ) : lots.length === 0 ? (
        <div className="text-center py-12 text-gray-500">Нет лотов</div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-x-auto">
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
                    <Link to={`/lots/${lot.id}`} className="text-primary hover:underline font-mono text-xs">{lot.id.slice(0, 8)}…</Link>
                  </td>
                  <td className="px-4 py-3 text-gray-700 dark:text-gray-300 max-w-xs truncate">{lot.raw_request_preview}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[lot.status] || 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'}`}>
                      {STATUS_LABELS[lot.status] || lot.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{lot.category || '—'}</td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs">{new Date(lot.created_at).toLocaleDateString('ru-RU')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-4">
          <button disabled={page <= 1} onClick={() => setPage(page - 1)}
            className="px-3 py-1 border rounded-lg text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">←</button>
          <span className="text-sm text-gray-600 dark:text-gray-400">Стр. {page} из {pages}</span>
          <button disabled={page >= pages} onClick={() => setPage(page + 1)}
            className="px-3 py-1 border rounded-lg text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">→</button>
        </div>
      )}
    </div>
  );
}
