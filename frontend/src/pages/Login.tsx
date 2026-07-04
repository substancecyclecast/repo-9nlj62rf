import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiErrorStatus, apiErrorDetail } from '../api/client';
import { Eye, EyeOff, Zap } from 'lucide-react';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const justRegistered = params.get('registered') === 'true';
  const isDemo = params.get('demo') === 'true';

  const handleDemoLogin = useCallback(async () => {
    setError('');
    setDemoLoading(true);
    try {
      await login('demo@snabagent.ru', 'Demo123!@#');
      navigate('/dashboard');
    } catch {
      setError('Демо-режим: войдите с email demo@snabagent.ru и паролем Demo123!@#');
    } finally {
      setDemoLoading(false);
    }
  }, [login, navigate]);

  useEffect(() => {
    if (isDemo) {
      handleDemoLogin();
    }
  }, [isDemo, handleDemoLogin]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      const status = apiErrorStatus(err);
      if (status === 401) setError('Неверный email или пароль');
      else if (status === 429) setError('Слишком много попыток. Подождите минуту');
      else setError(apiErrorDetail(err, 'Ошибка входа'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl p-8 w-full max-w-md border border-gray-100 dark:border-gray-800">
        <div className="flex items-center justify-center gap-2 mb-6">
          <img src="/logo.png" alt="SnabAgent" className="w-10 h-10 rounded-xl" />
          <span className="text-2xl font-bold text-gray-900 dark:text-white">SnabAgent</span>
        </div>

        <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-6 text-center">Вход в систему</h1>

        {justRegistered && (
          <div className="mb-4 p-3 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded-lg text-sm">
            Регистрация успешна! Войдите с вашим email и паролем.
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg text-sm">{error}</div>
        )}

        {/* Demo access button */}
        <button
          onClick={handleDemoLogin}
          disabled={demoLoading}
          className="w-full mb-4 flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-cyan-500 text-white py-3 rounded-xl hover:from-blue-700 hover:to-cyan-600 transition disabled:opacity-50 font-medium"
        >
          <Zap className="w-4 h-4" />
          {demoLoading ? 'Загрузка демо...' : 'Демо-доступ (без регистрации)'}
        </button>

        <div className="relative mb-4">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-200 dark:border-gray-700"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="bg-white dark:bg-gray-900 px-4 text-gray-400">или войдите</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Пароль</label>
            <div className="relative">
              <input type={showPw ? 'text' : 'password'} required value={password} onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2.5 pr-10 border border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent" />
              <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <button type="submit" disabled={loading}
            className="w-full bg-primary text-white py-2.5 rounded-xl hover:bg-primary-dark transition disabled:opacity-50 font-medium">
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
          Нет аккаунта? <Link to="/register" className="text-primary hover:underline font-medium">Зарегистрироваться</Link>
        </p>
      </div>
    </div>
  );
}
