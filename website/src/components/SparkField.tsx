import {useEffect, useRef} from 'react';

type Ember = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  life: number;
  maxLife: number;
  color: string;
  tw: number;
};

const COLORS = ['#FFD166', '#FF9E2C', '#FF6B1A', '#FFE7A3', '#E8452A'];

/**
 * A living field of rising embers — the "spark" in Iskra. Embers drift upward,
 * twinkle, and are born from the pointer so the hero answers the hand. Honors
 * prefers-reduced-motion (renders a single static scatter) and caps device
 * pixel ratio at 2. Cleans up every listener/observer/frame on unmount.
 */
export default function SparkField({className}: {className?: string}) {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = 0;
    let h = 0;
    let raf = 0;
    let embers: Ember[] = [];
    const pointer = {x: -9999, y: -9999, down: false};

    const makeEmber = (anywhere: boolean, at?: {x: number; y: number}): Ember => ({
      x: at ? at.x : Math.random() * w,
      y: at ? at.y : anywhere ? Math.random() * h : h + 8,
      vx: (Math.random() - 0.5) * 0.3,
      vy: -(0.25 + Math.random() * 0.75),
      r: 0.6 + Math.random() * 2.3,
      life: 0,
      maxLife: 4 + Math.random() * 6,
      color: COLORS[(Math.random() * COLORS.length) | 0],
      tw: Math.random() * Math.PI * 2,
    });

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      canvas.width = Math.max(1, Math.floor(w * dpr));
      canvas.height = Math.max(1, Math.floor(h * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const seed = () => {
      const target = Math.min(80, Math.floor((w * h) / 16000));
      embers = Array.from({length: target}, () => makeEmber(true));
    };

    const drawEmber = (e: Ember, alpha: number) => {
      ctx.globalAlpha = alpha;
      ctx.shadowBlur = e.r * 5;
      ctx.shadowColor = e.color;
      ctx.fillStyle = e.color;
      ctx.beginPath();
      ctx.arc(e.x, e.y, e.r, 0, Math.PI * 2);
      ctx.fill();
    };

    const staticScatter = () => {
      ctx.clearRect(0, 0, w, h);
      ctx.shadowBlur = 0;
      for (const e of embers) drawEmber(e, 0.5);
      ctx.globalAlpha = 1;
    };

    let last = performance.now();
    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      ctx.clearRect(0, 0, w, h);
      ctx.shadowBlur = 0;

      // Keep the field populated.
      const target = Math.min(80, Math.floor((w * h) / 16000));
      if (embers.length < target && Math.random() < 0.3) embers.push(makeEmber(false));

      for (let i = embers.length - 1; i >= 0; i--) {
        const e = embers[i];
        e.life += dt;
        e.tw += dt * 3;
        e.x += e.vx + Math.sin(e.tw) * 0.15;
        e.y += e.vy;

        // Gentle pull toward the pointer — the spark answers the hand.
        if (pointer.down) {
          const dx = pointer.x - e.x;
          const dy = pointer.y - e.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < 40000 && d2 > 1) {
            const d = Math.sqrt(d2);
            e.x += (dx / d) * 0.6;
            e.y += (dy / d) * 0.6;
          }
        }

        const fade =
          e.life < 0.6 ? e.life / 0.6 : e.life > e.maxLife - 1 ? Math.max(0, (e.maxLife - e.life)) : 1;
        const twinkle = 0.55 + 0.45 * Math.sin(e.tw);
        drawEmber(e, Math.max(0, Math.min(1, fade * twinkle)) * 0.9);

        if (e.life >= e.maxLife || e.y < -12 || e.x < -12 || e.x > w + 12) {
          embers.splice(i, 1);
        }
      }
      ctx.globalAlpha = 1;
      ctx.shadowBlur = 0;
      raf = requestAnimationFrame(tick);
    };

    const onMove = (ev: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      pointer.x = ev.clientX - rect.left;
      pointer.y = ev.clientY - rect.top;
      if (!reduce && Math.random() < 0.5) {
        embers.push(makeEmber(false, {x: pointer.x, y: pointer.y}));
      }
    };
    const onDown = (ev: PointerEvent) => {
      pointer.down = true;
      const rect = canvas.getBoundingClientRect();
      const x = ev.clientX - rect.left;
      const y = ev.clientY - rect.top;
      if (!reduce) {
        for (let i = 0; i < 14; i++) {
          const e = makeEmber(false, {x, y});
          const a = Math.random() * Math.PI * 2;
          const s = 0.5 + Math.random() * 1.6;
          e.vx = Math.cos(a) * s;
          e.vy = Math.sin(a) * s - 0.4;
          embers.push(e);
        }
      }
    };
    const onUp = () => {
      pointer.down = false;
    };
    const onLeave = () => {
      pointer.down = false;
      pointer.x = -9999;
      pointer.y = -9999;
    };

    resize();
    seed();

    const ro = new ResizeObserver(() => {
      resize();
      if (reduce) staticScatter();
    });
    ro.observe(canvas);

    if (reduce) {
      staticScatter();
    } else {
      canvas.addEventListener('pointermove', onMove);
      canvas.addEventListener('pointerdown', onDown);
      window.addEventListener('pointerup', onUp);
      canvas.addEventListener('pointerleave', onLeave);
      last = performance.now();
      raf = requestAnimationFrame(tick);
    }

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      canvas.removeEventListener('pointermove', onMove);
      canvas.removeEventListener('pointerdown', onDown);
      window.removeEventListener('pointerup', onUp);
      canvas.removeEventListener('pointerleave', onLeave);
    };
  }, []);

  return <canvas ref={ref} className={className} aria-hidden="true" />;
}