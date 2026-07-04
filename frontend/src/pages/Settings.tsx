import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Sun, Moon, Copy } from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuth();
  const { dark, toggle } = useTheme();
  const [copied, setCopied] = useState(false);

  const apiKey = localStorage.getItem('access_token') || '';
  const maskedKey = apiKey ? `${apiKey.slice(0, 12)}...${apiKey.slice(-6)}` : 'Не авторизован';

  const copyKey = () => {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Настройки</h1>

      {/* Profile */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 mb-6 border border-gray-100 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Профиль</h2>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Email</span>
            <span className="text-gray-900 dark:text-white">{user?.email}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Роль</span>
            <span className="text-gray-900 dark:text-white capitalize">{user?.role}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">ID</span>
            <span className="text-gray-900 dark:text-white font-mono text-xs">{user?.id}</span>
          </div>
        </div>
      </div>

      {/* Theme */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 mb-6 border border-gray-100 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Тема</h2>
        <button onClick={toggle}
          className="flex items-center gap-3 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition">
          {dark ? <Sun className="w-5 h-5 text-yellow-400" /> : <Moon className="w-5 h-5 text-gray-500" />}
          <span className="text-sm text-gray-700 dark:text-gray-300">{dark ? 'Светлая тема' : 'Тёмная тема'}</span>
        </button>
      </div>

      {/* API Key */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 mb-6 border border-gray-100 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">API Token</h2>
        <div className="flex items-center gap-2">
          <code className="flex-1 text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded-lg text-gray-600 dark:text-gray-300 font-mono truncate">
            {maskedKey}
          </code>
          <button onClick={copyKey}
            className="p-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition"
            title="Копировать">
            <Copy className="w-4 h-4 text-gray-500" />
          </button>
        </div>
        {copied && <p className="text-xs text-green-600 mt-1">Скопировано!</p>}
      </div>

      {/* Tariff */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Тариф</h2>
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full text-sm font-medium">
            Pilot (Пробный)
          </span>
          <span className="text-sm text-gray-500 dark:text-gray-400">14 дней бесплатно</span>
        </div>
      </div>
    </div>
  );
}
