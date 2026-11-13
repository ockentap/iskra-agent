import React, {useCallback, useEffect, useRef, useState} from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import SparkField from '../components/SparkField';
import styles from './index.module.css';

/* ------------------------------------------------------------------ */
/* Small primitives                                                    */
/* ------------------------------------------------------------------ */

function useCopy(): [boolean, (text: string) => void] {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const copy = useCallback((text: string) => {
    const done = () => {
      setCopied(true);
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setCopied(false), 1800);
    };
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(done);
    } else {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand('copy');
      } catch {
        /* noop */
      }
      document.body.removeChild(ta);
      done();
    }
  }, []);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  return [copied, copy];
}

function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            setSeen(true);
            io.disconnect();
          }
        }
      },
      {threshold: 0.15},
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div
      ref={ref}
      className={`${styles.reveal} ${seen ? styles.revealIn : ''} ${className ?? ''}`}
      style={{transitionDelay: `${delay}ms`}}>
      {children}
    </div>
  );
}

function ScrollProgress() {
  const [p, setP] = useState(0);
  useEffect(() => {
    const onScroll = () => {
      const doc = document.documentElement;
      const max = doc.scrollHeight - window.innerHeight;
      setP(max > 0 ? Math.min(1, window.scrollY / max) : 0);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, {passive: true});
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  return <div className={styles.progress} style={{transform: `scaleX(${p})`}} aria-hidden="true" />;
}

/* ------------------------------------------------------------------ */
/* Icons (inline stroke SVG, ember-tinted via currentColor)            */
/* ------------------------------------------------------------------ */

const ICON_PATHS: Record<string, React.ReactNode> = {
  loop: (
    <>
      <path d="M21 12a9 9 0 1 1-2.64-6.36" />
      <path d="M21 3v6h-6" />
      <circle cx="12" cy="12" r="2.4" />
    </>
  ),
  server: (
    <>
      <rect x="3" y="4" width="18" height="7" rx="2" />
      <rect x="3" y="13" width="18" height="7" rx="2" />
      <path d="M7 7.5h.01M7 16.5h.01" />
    </>
  ),
  chat: (
    <>
      <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7a8.5 8.5 0 1 1 16.1-3.8z" />
      <path d="M8.5 11.5h.01M12 11.5h.01M15.5 11.5h.01" />
    </>
  ),
  brain: (
    <>
      <path d="M12 4a3 3 0 0 0-3 3 3 3 0 0 0-3 3c0 1 .4 1.9 1.1 2.5A3 3 0 0 0 8 18a3 3 0 0 0 4 2.8" />
      <path d="M12 4a3 3 0 0 1 3 3 3 3 0 0 1 3 3c0 1-.4 1.9-1.1 2.5A3 3 0 0 1 16 18a3 3 0 0 1-4 2.8" />
      <path d="M12 4v16" />
    </>
  ),
  plug: (
    <>
      <path d="M9 2v6M15 2v6" />
      <path d="M6 8h12l-1.5 6a4 4 0 0 1-4 3h-1a4 4 0 0 1-4-3z" />
      <path d="M12 17v5" />
    </>
  ),
  mic: (
    <>
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0M12 17v5M8 22h8" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </>
  ),
  bots: (
    <>
      <rect x="4" y="8" width="16" height="11" rx="3" />
      <path d="M12 8V4M9 4h6" />
      <path d="M9 13h.01M15 13h.01M9.5 16.5h5" />
    </>
  ),
};

function Icon({name}: {name: string}) {
  return (
    <svg
      className={styles.featureIcon}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true">
      {ICON_PATHS[name]}
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* Content                                                             */
/* ------------------------------------------------------------------ */

const FEATURES = [
  {
    icon: 'loop',
    title: 'A closed learning loop',
    desc: 'Creates skills from experience, improves them during use, nudges itself to persist knowledge, and builds a deepening model of you across sessions.',
    wide: true,
  },
  {
    icon: 'server',
    title: 'Runs anywhere',
    desc: 'Six terminal backends — local, Docker, SSH, Daytona, Modal, Vercel Sandbox. A $5 VPS or a GPU cluster; it is not tied to your laptop.',
  },
  {
    icon: 'chat',
    title: 'Lives where you do',
    desc: 'CLI, Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Email and more — 20+ platforms from one gateway.',
  },
  {
    icon: 'brain',
    title: 'Memory & skills',
    desc: 'Persistent memory that grows across sessions, plus portable, shareable skills on the open agentskills.io standard.',
  },
  {
    icon: 'plug',
    title: 'Tools & MCP',
    desc: '60+ built-in tools and any MCP server. Search, browse, vision, image generation and TTS from one place.',
  },
  {
    icon: 'mic',
    title: 'Voice mode',
    desc: 'Real-time voice across CLI, Telegram and Discord — talk to it while it works.',
  },
  {
    icon: 'clock',
    title: 'Scheduled automations',
    desc: 'Built-in cron with delivery to any platform, so routines run while you sleep.',
  },
  {
    icon: 'bots',
    title: 'Bot Mode',
    desc: 'A durable team of specialist bots with their own model, memory and skills that collaborate through @mentions.',
    wide: true,
  },
];

const DOCS = [
  {to: '/docs/getting-started/quickstart', title: 'Quickstart', desc: 'Your first conversation and the features to try first.'},
  {to: '/docs/getting-started/installation', title: 'Installation', desc: 'Linux, macOS, WSL2, Windows, Nix and Android in 60 seconds.'},
  {to: '/docs/user-guide/cli', title: 'User Guide', desc: 'The CLI, TUI, desktop, configuration and the messaging gateway.'},
  {to: '/docs/developer-guide/architecture', title: 'Developer Guide', desc: 'Architecture, plugins, skills and extending the agent.'},
  {to: '/docs/reference/cli-commands', title: 'Reference', desc: 'Every command, environment variable and config key.'},
  {to: '/docs/user-guide/features/memory', title: 'Memory & Skills', desc: 'How the learning loop remembers and improves.'},
];

const INSTALL_UNIX = 'curl -fsSL https://ockentap.github.io/iskra-agent/install.sh | bash';
const INSTALL_WIN = 'iex (irm https://ockentap.github.io/iskra-agent/install.ps1)';

function InstallChip() {
  const [copied, copy] = useCopy();
  return (
    <div className={styles.installChip}>
      <span className={styles.installPrompt}>$</span>
      <code className={styles.installCmd}>{INSTALL_UNIX}</code>
      <button
        type="button"
        className={styles.copyBtn}
        onClick={() => copy(INSTALL_UNIX)}
        aria-label="Copy install command">
        {copied ? 'Copied ✓' : 'Copy'}
      </button>
    </div>
  );
}

function InstallPanel() {
  const [tab, setTab] = useState<'unix' | 'win'>('unix');
  const [copied, copy] = useCopy();
  const cmd = tab === 'unix' ? INSTALL_UNIX : INSTALL_WIN;
  return (
    <div className={styles.terminal}>
      <div className={styles.terminalBar}>
        <span className={styles.dot} data-c="r" />
        <span className={styles.dot} data-c="y" />
        <span className={styles.dot} data-c="g" />
        <span className={styles.terminalTitle}>install — iskra</span>
        <div className={styles.tabs} role="tablist" aria-label="Platform">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'unix'}
            className={tab === 'unix' ? styles.tabOn : styles.tab}
            onClick={() => setTab('unix')}>
            Linux · macOS · WSL2
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'win'}
            className={tab === 'win' ? styles.tabOn : styles.tab}
            onClick={() => setTab('win')}>
            Windows
          </button>
        </div>
      </div>
      <div className={styles.terminalBody}>
        <span className={styles.installPrompt}>{tab === 'unix' ? '$' : '>'}</span>
        <code className={styles.terminalCmd}>{cmd}</code>
        <button type="button" className={styles.copyBtn} onClick={() => copy(cmd)}>
          {copied ? 'Copied ✓' : 'Copy'}
        </button>
      </div>
      <p className={styles.terminalNote}>
        One command clones the fork, sets up Python, and publishes the <code>iskra</code> CLI. Then run{' '}
        <code>iskra setup</code> to pick a model and start talking.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function Home(): React.ReactElement {
  const logo = useBaseUrl('/img/logo.svg');
  return (
    <Layout
      title="Iskra — the self-improving AI agent"
      description="Iskra is a spark of a fork of Hermes Agent: an autonomous agent with a built-in learning loop that creates skills from experience and remembers across sessions.">
      <div className={styles.page}>
        <ScrollProgress />

        {/* HERO */}
        <header className={styles.hero}>
          <div className={styles.aurora} aria-hidden="true" />
          <SparkField className={styles.sparkCanvas} />
          <div className={styles.grain} aria-hidden="true" />
          <div className={styles.heroInner}>
            <img src={logo} alt="" className={styles.emblem} />
            <h1 className={styles.wordmark}>
              iskra<span className={styles.wordmarkSpark} aria-hidden="true" />
            </h1>
            <p className={styles.tagline}>The self-improving AI agent</p>
            <p className={styles.lede}>
              A spark that keeps learning. Iskra creates skills from experience, improves them as it
              works, and remembers you across sessions — running anywhere, reachable from anywhere.
            </p>
            <div className={styles.ctaRow}>
              <Link className={styles.btnPrimary} to="/docs/getting-started/quickstart">
                Get started
                <span aria-hidden="true"> →</span>
              </Link>
              <a
                className={styles.btnGhost}
                href="https://github.com/ockentap/iskra-agent"
                target="_blank"
                rel="noreferrer">
                View on GitHub
              </a>
            </div>
            <InstallChip />
          </div>
          <div className={styles.scrollHint} aria-hidden="true">
            <span className={styles.scrollHintLine} />
            scroll
          </div>
        </header>

        <main className={styles.main}>
          {/* WHAT / LEARNING LOOP */}
          <section className={`${styles.section} ${styles.tintA}`}>
            <Reveal>
              <p className={styles.kicker}>Why “iskra”</p>
              <h2 className={styles.h2}>
                <em>Iskra</em> is Bosnian for <span className={styles.ember}>spark</span>.
              </h2>
              <p className={styles.body}>
                Not a copilot tethered to an IDE, not a wrapper around one API. An autonomous agent
                that gets more capable the longer it runs — a small spark that catches, spreads, and
                keeps burning. It lives on a $5 VPS or a GPU cluster, and you talk to it from Telegram
                while it works away on its own.
              </p>
            </Reveal>
            <div className={styles.loop}>
              {[
                {n: '01', t: 'Remember', d: 'Cross-session memory with full-text recall and a deepening model of who you are.'},
                {n: '02', t: 'Learn', d: 'Turns experience into reusable skills, then improves them during use.'},
                {n: '03', t: 'Improve', d: 'Nudges itself to persist knowledge, so every session starts a little sharper.'},
              ].map((s, i) => (
                <Reveal key={s.n} delay={i * 120} className={styles.loopCardWrap}>
                  <div className={styles.loopCard}>
                    <span className={styles.loopNum}>{s.n}</span>
                    <h3 className={styles.loopTitle}>{s.t}</h3>
                    <p className={styles.loopDesc}>{s.d}</p>
                  </div>
                  {i < 2 && <span className={styles.loopArrow} aria-hidden="true">✦</span>}
                </Reveal>
              ))}
            </div>
          </section>

          {/* FEATURES */}
          <section className={`${styles.section} ${styles.tintB}`}>
            <Reveal>
              <p className={styles.kicker}>What it does</p>
              <h2 className={styles.h2}>Built to keep getting better.</h2>
            </Reveal>
            <div className={styles.featureGrid}>
              {FEATURES.map((f, i) => (
                <Reveal key={f.title} delay={(i % 4) * 90} className={f.wide ? styles.featureWide : ''}>
                  <article className={styles.featureCard}>
                    <span className={styles.featureIconWrap}>
                      <Icon name={f.icon} />
                    </span>
                    <h3 className={styles.featureTitle}>{f.title}</h3>
                    <p className={styles.featureDesc}>{f.desc}</p>
                  </article>
                </Reveal>
              ))}
            </div>
          </section>

          {/* INSTALL */}
          <section className={`${styles.section} ${styles.tintA}`}>
            <Reveal>
              <p className={styles.kicker}>Get it running</p>
              <h2 className={styles.h2}>One command to a working agent.</h2>
              <p className={styles.body}>
                Iskra installs from the fork in about a minute. Pick your platform, copy the command,
                and run <code>iskra setup</code> to choose a model.
              </p>
            </Reveal>
            <Reveal delay={120}>
              <InstallPanel />
            </Reveal>
          </section>

          {/* DOCS */}
          <section className={`${styles.section} ${styles.tintB}`}>
            <Reveal>
              <p className={styles.kicker}>Documentation</p>
              <h2 className={styles.h2}>Everything, in the open.</h2>
            </Reveal>
            <div className={styles.docsGrid}>
              {DOCS.map((d, i) => (
                <Reveal key={d.to} delay={(i % 3) * 90}>
                  <Link to={d.to} className={styles.docCard}>
                    <span className={styles.docTitle}>{d.title}</span>
                    <span className={styles.docDesc}>{d.desc}</span>
                    <span className={styles.docArrow} aria-hidden="true">→</span>
                  </Link>
                </Reveal>
              ))}
            </div>
          </section>

          {/* CTA */}
          <section className={`${styles.section} ${styles.ctaBand}`}>
            <Reveal>
              <div className={styles.ctaInner}>
                <img src={logo} alt="" className={styles.ctaEmblem} />
                <h2 className={styles.ctaTitle}>Strike the spark.</h2>
                <p className={styles.body}>
                  Free, MIT-licensed, and a fork of Hermes Agent by Nous Research. Bring your own
                  model endpoint and let it learn.
                </p>
                <div className={styles.ctaRow}>
                  <Link className={styles.btnPrimary} to="/docs/getting-started/installation">
                    Install Iskra
                  </Link>
                  <Link className={styles.btnGhost} to="/docs/getting-started/quickstart">
                    Read the quickstart
                  </Link>
                </div>
              </div>
            </Reveal>
          </section>
        </main>
      </div>
    </Layout>
  );
}