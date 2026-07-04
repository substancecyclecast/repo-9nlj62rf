import { Link } from 'react-router-dom';
import {
  Bot, Zap, Shield, ArrowRight, CheckCircle, BarChart3,
  Globe, Lock, Cpu, Mail,
  Star, TrendingUp, Users, FileText
} from 'lucide-react';

const FEATURES = [
  {
    icon: Bot,
    title: 'Мульти-агентный AI',
    desc: '6 специализированных агентов: планирование, поиск поставщиков, переговоры, верификация, отчётность',
    color: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
  },
  {
    icon: Zap,
    title: '15 минут вместо 5 дней',
    desc: 'Полный цикл закупки от заявки до обоснованного выбора поставщика',
    color: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  },
  {
    icon: Shield,
    title: 'Двойная верификация',
    desc: 'Результат основного LLM проверяется независимой моделью — защита от галлюцинаций',
    color: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  },
  {
    icon: BarChart3,
    title: 'Экономия 8-30%',
    desc: 'Оптимальный выбор из 6+ поставщиков с автоматическими переговорами по цене',
    color: 'bg-violet-500/10 text-violet-600 dark:text-violet-400',
  },
  {
    icon: Lock,
    title: 'Enterprise-безопасность',
    desc: 'SSO/SAML, Row-Level Security, PII-маскирование, 152-ФЗ compliance',
    color: 'bg-rose-500/10 text-rose-600 dark:text-rose-400',
  },
  {
    icon: Globe,
    title: 'Российские LLM',
    desc: 'GigaChat, YandexGPT — данные не покидают территорию РФ',
    color: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400',
  },
];

const STEPS = [
  {
    num: '01',
    title: 'Создайте заявку',
    desc: 'Опишите потребность в свободной форме или загрузите ТЗ (PDF/DOCX/Excel)',
    icon: FileText,
  },
  {
    num: '02',
    title: 'AI обрабатывает',
    desc: 'Парсинг позиций, классификация, поиск по базе 55+ поставщиков + веб-скрейпинг',
    icon: Cpu,
  },
  {
    num: '03',
    title: 'Автоматические RFQ',
    desc: 'Формирование и отправка запросов коммерческих предложений поставщикам',
    icon: Mail,
  },
  {
    num: '04',
    title: 'Готовый отчёт',
    desc: 'Топ-3 поставщика, сравнительная таблица, обоснование НМЦК, экономия',
    icon: TrendingUp,
  },
];

const PRICING = [
  {
    name: 'Pilot',
    price: 'Бесплатно',
    period: '14 дней',
    features: ['До 100 лотов', '1 пользователь', 'Email-поддержка', 'Базовая аналитика', 'Telegram-бот'],
    cta: 'Начать пилот',
    highlight: false,
  },
  {
    name: 'Professional',
    price: '49 000 ₽',
    period: '/мес',
    features: ['До 1 000 лотов/мес', 'До 10 пользователей', 'Telegram-бот + Web', 'Полная аналитика', 'Приоритетная поддержка', 'Экспорт Excel'],
    cta: 'Выбрать Pro',
    highlight: true,
  },
  {
    name: 'Enterprise',
    price: 'Индивидуально',
    period: '',
    features: ['Безлимитные лоты', 'Неограниченно пользователей', 'SSO/SAML интеграция', 'On-premise деплой', 'SLA 99.9%', 'Выделенный менеджер', 'API-интеграция'],
    cta: 'Связаться',
    highlight: false,
  },
];

const STATS = [
  { value: '15 мин', label: 'Среднее время обработки' },
  { value: '8-30%', label: 'Экономия на закупках' },
  { value: '6', label: 'AI-агентов в пайплайне' },
  { value: '10 000+', label: 'SKU в месяц' },
];

const TESTIMONIALS = [
  {
    quote: 'Сократили время обработки заявок с 5 дней до 20 минут. Экономия по MRO-категории — 12% за первый квартал.',
    author: 'Иван Петров',
    role: 'Руководитель отдела закупок',
    company: 'Промышленный холдинг',
  },
  {
    quote: 'Автоматические RFQ и сравнительные таблицы — то, чего нам не хватало. Верификация двумя моделями — отличная идея.',
    author: 'Анна Сидорова',
    role: 'Procurement Director',
    company: 'IT-компания',
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
      {/* NAVBAR */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 dark:bg-gray-950/80 border-b border-gray-100 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="SnabAgent" className="w-8 h-8 rounded-lg" />
            <span className="text-xl font-bold text-gray-900 dark:text-white">SnabAgent</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm text-gray-600 dark:text-gray-300 hover:text-primary transition">Возможности</a>
            <a href="#how" className="text-sm text-gray-600 dark:text-gray-300 hover:text-primary transition">Как работает</a>
            <a href="#pricing" className="text-sm text-gray-600 dark:text-gray-300 hover:text-primary transition">Тарифы</a>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login?demo=true" className="text-sm text-primary font-medium hover:text-primary-dark transition">
              Демо-доступ
            </Link>
            <Link to="/login" className="text-sm text-gray-600 dark:text-gray-300 hover:text-primary transition">Войти</Link>
            <Link to="/register" className="text-sm bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-dark transition">
              Попробовать бесплатно
            </Link>
          </div>
        </div>
      </nav>

      {/* HERO */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 hero-gradient opacity-5"></div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 md:py-28 text-center relative">
          <div className="inline-flex items-center gap-2 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 px-4 py-2 rounded-full text-sm font-medium mb-8">
            <Zap className="w-4 h-4" />
            AI-платформа для корпоративных закупок
          </div>
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-gray-900 dark:text-white mb-6 leading-tight">
            Закупки на{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-500">
              автопилоте
            </span>
          </h1>
          <p className="text-lg md:text-xl text-gray-600 dark:text-gray-400 max-w-3xl mx-auto mb-10">
            6 AI-агентов автоматически находят поставщиков, ведут переговоры,
            проверяют контрагентов и формируют обоснование НМЦК.
            Экономьте до 30% бюджета и 80% времени.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/login?demo=true" className="inline-flex items-center justify-center gap-2 bg-primary text-white px-8 py-4 rounded-xl text-lg font-medium hover:bg-primary-dark transition shadow-lg shadow-blue-500/25">
              Попробовать демо <ArrowRight className="w-5 h-5" />
            </Link>
            <a href="#how" className="inline-flex items-center justify-center gap-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 px-8 py-4 rounded-xl text-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition">
              Как это работает
            </a>
          </div>
        </div>
      </section>

      {/* STATS */}
      <section className="border-y border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {STATS.map(({ value, label }) => (
              <div key={label} className="text-center">
                <div className="text-3xl md:text-4xl font-bold text-primary mb-1">{value}</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" className="py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              Почему SnabAgent?
            </h2>
            <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              Первая в России мульти-агентная AI-платформа для промышленных закупок
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map(({ icon: Icon, title, desc, color }) => (
              <div key={title} className="card-hover bg-white dark:bg-gray-800 p-6 rounded-2xl border border-gray-100 dark:border-gray-700">
                <div className={`w-12 h-12 ${color} rounded-xl flex items-center justify-center mb-4`}>
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">{title}</h3>
                <p className="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="py-20 md:py-28 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              Как это работает
            </h2>
            <p className="text-lg text-gray-600 dark:text-gray-400">
              От заявки до выбора поставщика — 4 простых шага
            </p>
          </div>
          <div className="grid md:grid-cols-4 gap-8">
            {STEPS.map(({ num, title, desc, icon: Icon }) => (
              <div key={num} className="relative text-center">
                <div className="w-16 h-16 mx-auto mb-4 bg-primary/10 rounded-2xl flex items-center justify-center">
                  <Icon className="w-8 h-8 text-primary" />
                </div>
                <div className="text-xs font-bold text-primary mb-2">ШАГ {num}</div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">{title}</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ARCHITECTURE */}
      <section className="py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              Архитектура AI-пайплайна
            </h2>
            <p className="text-lg text-gray-600 dark:text-gray-400">
              6 специализированных агентов на базе LangGraph
            </p>
          </div>
          <div className="grid md:grid-cols-6 gap-4">
            {[
              { name: 'Planner', desc: 'Парсинг заявки', color: 'from-blue-500 to-blue-600' },
              { name: 'Sourcer', desc: 'Поиск поставщиков', color: 'from-cyan-500 to-cyan-600' },
              { name: 'Communicator', desc: 'Отправка RFQ', color: 'from-emerald-500 to-emerald-600' },
              { name: 'Negotiator', desc: 'Переговоры', color: 'from-amber-500 to-amber-600' },
              { name: 'Verifier', desc: 'Верификация', color: 'from-purple-500 to-purple-600' },
              { name: 'Reporter', desc: 'Итоговый отчёт', color: 'from-rose-500 to-rose-600' },
            ].map(({ name, desc, color }, i) => (
              <div key={name} className="relative">
                <div className={`bg-gradient-to-br ${color} rounded-2xl p-4 text-white text-center`}>
                  <div className="text-xs opacity-75 mb-1">Агент {i + 1}</div>
                  <div className="font-bold text-sm">{name}</div>
                  <div className="text-xs mt-1 opacity-90">{desc}</div>
                </div>
                {i < 5 && (
                  <div className="hidden md:block absolute top-1/2 -right-3 transform -translate-y-1/2 text-gray-300 dark:text-gray-600">
                    <ArrowRight className="w-5 h-5" />
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="mt-8 text-center">
            <div className="inline-flex items-center gap-2 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 px-4 py-2 rounded-full text-sm">
              <CheckCircle className="w-4 h-4" />
              Двойная верификация: основная LLM + независимый верификатор
            </div>
          </div>
        </div>
      </section>

      {/* TESTIMONIALS */}
      <section className="py-20 md:py-28 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              Отзывы клиентов
            </h2>
          </div>
          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {TESTIMONIALS.map(({ quote, author, role, company }) => (
              <div key={author} className="bg-white dark:bg-gray-800 p-8 rounded-2xl border border-gray-100 dark:border-gray-700">
                <div className="flex gap-1 mb-4">
                  {[1, 2, 3, 4, 5].map((s) => (
                    <Star key={s} className="w-4 h-4 text-amber-400 fill-amber-400" />
                  ))}
                </div>
                <p className="text-gray-700 dark:text-gray-300 mb-6 italic">"{quote}"</p>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                    <Users className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <div className="font-semibold text-gray-900 dark:text-white text-sm">{author}</div>
                    <div className="text-xs text-gray-500">{role}, {company}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* PRICING */}
      <section id="pricing" className="py-20 md:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              Тарифы
            </h2>
            <p className="text-lg text-gray-600 dark:text-gray-400">
              Начните бесплатно, масштабируйте по мере роста
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {PRICING.map(({ name, price, period, features, cta, highlight }) => (
              <div key={name} className={`bg-white dark:bg-gray-800 p-8 rounded-2xl relative card-hover ${highlight ? 'ring-2 ring-primary shadow-xl shadow-blue-500/10' : 'border border-gray-200 dark:border-gray-700'}`}>
                {highlight && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-white text-xs px-4 py-1 rounded-full font-medium">
                    Популярный
                  </span>
                )}
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">{name}</h3>
                <div className="mt-4 mb-6">
                  <span className="text-3xl font-bold text-gray-900 dark:text-white">{price}</span>
                  {period && <span className="text-gray-500 ml-1">{period}</span>}
                </div>
                <ul className="space-y-3 mb-8">
                  {features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <CheckCircle className="w-4 h-4 text-primary flex-shrink-0" /> {f}
                    </li>
                  ))}
                </ul>
                <Link to={name === 'Enterprise' ? '/register' : '/register'} className={`block text-center py-3 rounded-xl font-medium transition ${highlight ? 'bg-primary text-white hover:bg-primary-dark' : 'border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
                  {cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TECH STACK */}
      <section className="py-20 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">Технологии</h2>
          </div>
          <div className="flex flex-wrap justify-center gap-4">
            {['LangGraph', 'GigaChat', 'YandexGPT', 'FastAPI', 'React 19', 'PostgreSQL', 'Qdrant', 'Redis', 'Celery', 'Docker', 'Playwright', 'Prometheus'].map((tech) => (
              <span key={tech} className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm text-gray-700 dark:text-gray-300 font-medium">
                {tech}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 md:py-28">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-6">
            Готовы автоматизировать закупки?
          </h2>
          <p className="text-lg text-gray-600 dark:text-gray-400 mb-8">
            Попробуйте демо-версию прямо сейчас — без регистрации
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/login?demo=true" className="inline-flex items-center justify-center gap-2 bg-primary text-white px-8 py-4 rounded-xl text-lg font-medium hover:bg-primary-dark transition shadow-lg shadow-blue-500/25">
              Демо-доступ <ArrowRight className="w-5 h-5" />
            </Link>
            <a href="mailto:scaleblinkk@vk.com" className="inline-flex items-center justify-center gap-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 px-8 py-4 rounded-xl text-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition">
              Связаться с нами
            </a>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <img src="/logo.png" alt="SnabAgent" className="w-8 h-8 rounded-lg" />
                <span className="text-lg font-bold text-gray-900 dark:text-white">SnabAgent</span>
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                AI-платформа автоматизации корпоративных закупок
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-white mb-3 text-sm">Продукт</h4>
              <ul className="space-y-2 text-sm text-gray-500 dark:text-gray-400">
                <li><a href="#features" className="hover:text-primary transition">Возможности</a></li>
                <li><a href="#pricing" className="hover:text-primary transition">Тарифы</a></li>
                <li><Link to="/login?demo=true" className="hover:text-primary transition">Демо</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-white mb-3 text-sm">Технологии</h4>
              <ul className="space-y-2 text-sm text-gray-500 dark:text-gray-400">
                <li>LangGraph + LangChain</li>
                <li>GigaChat / YandexGPT</li>
                <li>FastAPI + React 19</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-white mb-3 text-sm">Контакты</h4>
              <ul className="space-y-2 text-sm text-gray-500 dark:text-gray-400">
                <li><a href="mailto:scaleblinkk@vk.com" className="hover:text-primary transition">scaleblinkk@vk.com</a></li>
                <li>Telegram: @snabagent</li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-200 dark:border-gray-800 mt-8 pt-8 text-center text-sm text-gray-500 dark:text-gray-400">
            &copy; {new Date().getFullYear()} SnabAgent. Все права защищены.
          </div>
        </div>
      </footer>
    </div>
  );
}
