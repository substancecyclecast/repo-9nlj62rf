import { useEffect, useState } from 'react';
import api from '../api/client';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const STATUS_LABELS: Record<string, string> = {
  draft: 'Черновик', planned: 'Запланирован', sourcing: 'Поиск',
  rfq_sent: 'Запросы', responses_collected: 'Ответы',
  negotiating: 'Переговоры', verified: 'Проверено', report_ready: 'Отчёт',
  approved: 'Одобрен', rejected: 'Отклонён', escalated: 'Эскалирован', failed: 'Ошибка',
};

const COLORS = ['#16a34a', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16'];

export default function Analytics() {
  const [statusData, setStatusData] = useState<{ name: string; value: number }[]>([]);
  const [categoryData, setCategoryData] = useState<{ name: string; count: number }[]>([]);
  const [totalLots, setTotalLots] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/lots', { params: { page_size: 100 } })
      .then((r) => {
        const items: { status: string; category: string | null }[] = r.data.items || [];
        setTotalLots(r.data.total || items.length);

        // Status distribution
        const statusMap: Record<string, number> = {};
        items.forEach((l) => {
          statusMap[l.status] = (statusMap[l.status] || 0) + 1;
        });
        setStatusData(
          Object.entries(statusMap).map(([k, v]) => ({
            name: STATUS_LABELS[k] || k,
            value: v,
          }))
        );

        // Category distribution
        const catMap: Record<string, number> = {};
        items.forEach((l) => {
          const cat = l.category || 'Без категории';
          catMap[cat] = (catMap[cat] || 0) + 1;
        });
        setCategoryData(
          Object.entries(catMap)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10)
            .map(([name, count]) => ({ name, count }))
        );
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-12 text-gray-500">Загрузка...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Аналитика</h1>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Pie: status */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Лоты по статусам <span className="text-sm text-gray-400 font-normal">({totalLots})</span>
          </h2>
          {statusData.length === 0 ? (
            <div className="text-center py-8 text-gray-500">Нет данных</div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={statusData} cx="50%" cy="50%" outerRadius={80} innerRadius={30} dataKey="value" label={({ name, value }) => `${name}: ${value}`} labelLine={false}>
                  {statusData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Bar: categories */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Лоты по категориям</h2>
          {categoryData.length === 0 ? (
            <div className="text-center py-8 text-gray-500">Нет данных</div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={categoryData}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#16a34a" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* KPI summary */}
      <div className="mt-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Сводка</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-3xl font-bold text-primary">{totalLots}</div>
            <div className="text-sm text-gray-500">Всего лотов</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-green-600">{statusData.find((d) => d.name === 'Одобрен')?.value || 0}</div>
            <div className="text-sm text-gray-500">Одобрено</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-yellow-600">{statusData.filter((d) => ['Поиск', 'Переговоры', 'Запросы'].includes(d.name)).reduce((s, d) => s + d.value, 0)}</div>
            <div className="text-sm text-gray-500">В работе</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-red-600">{statusData.find((d) => d.name === 'Эскалирован')?.value || 0}</div>
            <div className="text-sm text-gray-500">Эскалировано</div>
          </div>
        </div>
      </div>
    </div>
  );
}
