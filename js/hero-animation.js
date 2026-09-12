/**
 * NAGDEV PRODUCTS PRIVATE LIMITED — HERO PIPELINE & PROCESS FLOW
 * Centerpiece interactive visualization of amber castor oil refining and pipeline flow.
 */

class HeroRefineryAnimation {
  constructor() {
    this.container = document.querySelector('.hero-visual-card');
    this.svg = document.querySelector('.pipeline-svg');
    this.primaryStream = document.querySelector('.oil-stream-primary');
    this.glowStream = document.querySelector('.oil-stream-glow');
    this.dripElement = document.querySelector('.oil-drip');
    this.gaugeNeedle = document.querySelector('.gauge-needle');
    
    this.isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.init();
  }

  init() {
    if (!this.container || this.isReducedMotion) return;
    this.bindMouseGlow();
  }

  bindMouseGlow() {
    this.container.addEventListener('mousemove', (e) => {
      const rect = this.container.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const xPct = Math.round((x / rect.width) * 100);
      const yPct = Math.round((y / rect.height) * 100);
      
      this.container.style.background = `radial-gradient(circle at ${xPct}% ${yPct}%, #183729 0%, #0d1e16 60%, #06110c 100%)`;
      
      if (this.gaugeNeedle) {
        const angle = -45 + (xPct / 100) * 90;
        this.gaugeNeedle.style.transform = `rotate(${angle}deg)`;
      }
    });

    this.container.addEventListener('mouseleave', () => {
      this.container.style.background = 'radial-gradient(circle at 50% 30%, #152f23 0%, #0c1d15 70%, #06110c 100%)';
      if (this.gaugeNeedle) {
        this.gaugeNeedle.style.transform = 'rotate(15deg)';
      }
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new HeroRefineryAnimation();
});
