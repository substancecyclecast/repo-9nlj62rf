import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { apiErrorDetail } from '../api/client';

const PHASES = [
  { value: 'pre_nmck', label: 'До НМЦК — предварительный расчёт' },
  { value: 'post_tender_published', label: 'После публикации тендера' },
  { value: 'unregulated', label: 'Нерегулируемая закупка' },
];

export default function NewLot() {
  const navigate = useNavigate();
  const [description, setDescription] = useState('');
  const [phase, setPhase] = useState('pre_nmck');
  const [budget, setBudget] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (description.length < 10) {
      setError('Описание должно быть минимум 10 символов');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const resp = await api.post('/lots', {
        raw_request: description,
        phase,
        total_estimated_rub: budget ? parseFloat(budget) : null,
      });
      setSuccess(`Лот создан: ${resp.data.id}`);
      setTimeout(() => navigate(`/lots/${resp.data.id}`), 1500);
    } catch (err) {
      setError(apiErrorDetail(err, 'Ошибка создания лота'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Новый лот</h1>

      {success && (
        <div className="mb-4 p-3 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded-lg text-sm">{success}</div>
      )}
      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg text-sm">{error}</div>
      )}

      <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 space-y-5 border border-gray-100 dark:border-gray-700">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Описание заявки</label>
          <textarea
            rows={5}
            required
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Опишите что нужно закупить. Например: Труба стальная 108х4 ГОСТ 10704-91, 500 м, доставка Тюмень..."
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
          />
          <div className="text-xs text-gray-400 mt-1">{description.length} / 50000</div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Фаза закупки</label>
            <select
              value={phase}
              onChange={(e) => setPhase(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              {PHASES.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Бюджет (₽)</label>
            <input
              type="number"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="Необязательно"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-primary text-white py-2.5 rounded-lg hover:bg-primary-dark transition disabled:opacity-50"
        >
          {loading ? 'Создание...' : 'Создать лот'}
        </button>
      </form>
    </div>
  );
}
