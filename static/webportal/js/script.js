// ---------- Lenis Smooth Scroll ----------
const lenis = new Lenis({
  duration: 1.1,
  easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
  direction: 'vertical',
  gestureDirection: 'vertical',
  smooth: true,
  mouseMultiplier: 1,
  smoothTouch: false,
  touchMultiplier: 2,
  infinite: false,
});

if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add((time) => {
    lenis.raf(time * 1000);
  });
  gsap.ticker.lagSmoothing(0);
} else {
  function raf(time) {
    lenis.raf(time);
    requestAnimationFrame(raf);
  }
  requestAnimationFrame(raf);
}

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// ---------- Scroll progress bar ----------
const progressBar = document.querySelector('.scroll-progress-bar');
function updateProgress() {
  const h = document.documentElement;
  const scrolled = h.scrollTop || document.body.scrollTop;
  const max = h.scrollHeight - h.clientHeight;
  if (progressBar) progressBar.style.width = (max > 0 ? (scrolled / max) * 100 : 0) + '%';
}
lenis.on('scroll', updateProgress);

// ---------- Header scrolled state ----------
const header = document.querySelector('.site-header');
lenis.on('scroll', ({ scroll }) => {
  if (header) header.classList.toggle('scrolled', scroll > 40);
});

// ---------- Nav scroll-spy ----------
const navLinks = Array.from(document.querySelectorAll('[data-nav]'));
const navTargets = navLinks.map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);

// ---------- Smooth-scroll anchor clicks via Lenis ----------
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', (e) => {
    const id = a.getAttribute('href');
    if (id.length > 1) {
      const target = document.querySelector(id);
      if (target) {
        e.preventDefault();
        lenis.scrollTo(target, { offset: -80, duration: 1.4 });
      }
    }
  });
});

// ---------- Magnetic buttons ----------
if (!prefersReducedMotion) {
  document.querySelectorAll('.magnetic').forEach(el => {
    let bound = el.getBoundingClientRect();
    el.addEventListener('mouseenter', () => { bound = el.getBoundingClientRect(); });
    el.addEventListener('mousemove', (e) => {
      const relX = e.clientX - bound.left - bound.width / 2;
      const relY = e.clientY - bound.top - bound.height / 2;
      el.style.transform = `translate(${relX * 0.22}px, ${relY * 0.4}px)`;
    });
    el.addEventListener('mouseleave', () => { el.style.transform = ''; });
  });
}

// ---------- FAQ accordion ----------
document.querySelectorAll('.faq-item').forEach(item => {
  const btn = item.querySelector('.faq-q');
  const panel = item.querySelector('.faq-a');
  btn.addEventListener('click', () => {
    const isOpen = item.classList.contains('open');
    document.querySelectorAll('.faq-item.open').forEach(other => {
      if (other !== item) {
        other.classList.remove('open');
        other.querySelector('.faq-a').style.maxHeight = 0;
      }
    });
    if (isOpen) {
      item.classList.remove('open');
      panel.style.maxHeight = 0;
    } else {
      item.classList.add('open');
      panel.style.maxHeight = panel.scrollHeight + 'px';
    }
  });
});

// ---------- Pricing billing toggle ----------
const billingToggle = document.getElementById('billingToggle');
const toggleLabels = document.querySelectorAll('.toggle-label');
const priceAmounts = document.querySelectorAll('.price-amount[data-monthly]');
if (billingToggle) {
  billingToggle.addEventListener('click', () => {
    const annual = !billingToggle.classList.contains('annual');
    billingToggle.classList.toggle('annual', annual);
    toggleLabels.forEach(l => l.classList.toggle('active', (l.dataset.period === 'annual') === annual));
    priceAmounts.forEach(el => {
      const val = annual ? el.dataset.annual : el.dataset.monthly;
      el.textContent = '₹' + Number(val).toLocaleString('en-IN');
    });
  });
}

// ---------- Animated counters ----------
function animateCounter(el) {
  const target = parseFloat(el.dataset.count);
  const suffix = el.dataset.suffix || '';
  const duration = 1400;
  const start = performance.now();
  function tick(now) {
    const p = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - p, 3);
    const val = Math.round(target * eased);
    el.textContent = val + suffix;
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

const counterObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      animateCounter(entry.target);
    } else {
      entry.target.textContent = '0' + (entry.target.dataset.suffix || '');
    }
  });
}, { threshold: 0.5 });
document.querySelectorAll('.stat-number').forEach(el => counterObserver.observe(el));

// ---------- Cursor-aware tilt ----------
if (!prefersReducedMotion && window.matchMedia('(pointer: fine)').matches) {
  document.querySelectorAll('.tilt-card').forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      card.style.transform = `perspective(900px) rotateY(${x * 10}deg) rotateX(${-y * 10}deg) scale3d(1.03,1.03,1.03)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });
}

// ---------- Gallery drag-to-scroll ----------
const galleryTrack = document.querySelector('.gallery-track');
if (galleryTrack) {
  let isDown = false, startX, scrollLeftStart;
  galleryTrack.addEventListener('pointerdown', (e) => {
    isDown = true; startX = e.clientX; scrollLeftStart = galleryTrack.scrollLeft || 0;
    galleryTrack.style.cursor = 'grabbing';
  });
  window.addEventListener('pointerup', () => { 
    isDown = false;
    galleryTrack.style.cursor = 'grab';
  });
  window.addEventListener('pointermove', (e) => {
    if (!isDown) return;
    e.preventDefault();
    const x = e.clientX;
    const walk = (x - startX) * 1.5;
    galleryTrack.scrollLeft = scrollLeftStart - walk;
  });
}

// ---------- GSAP ScrollTrigger animations ----------
if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined' && !prefersReducedMotion) {
  gsap.registerPlugin(ScrollTrigger);
  ScrollTrigger.config({ ignoreMobileResize: true });

  gsap.set('.fan-wrapper', { xPercent: 35 });

  // Hero entrance sequence
  const heroTl = gsap.timeline({ delay: 0.1 });
  heroTl
    .from('.hero .eyebrow', { y: 24, opacity: 0, duration: 0.7, ease: 'power3.out' })
    .from('.hero h1', { y: 32, opacity: 0, duration: 0.9, ease: 'power3.out' }, '-=0.4')
    .from('.hero-subtitle', { y: 20, opacity: 0, duration: 0.7, ease: 'power3.out' }, '-=0.5')
    .from('.hero-actions', { y: 18, opacity: 0, duration: 0.7, ease: 'power3.out' }, '-=0.5')
    .from('.fan-wrapper', { y: 50, opacity: 0, duration: 1, stagger: 0.1, ease: 'power3.out' }, '-=0.3');

  // Fan cards scroll animation
  gsap.to('.fan-wrapper', {
    xPercent: -20,
    ease: 'none',
    stagger: 0.12,
    scrollTrigger: {
      trigger: '.hero',
      start: 'top top',
      end: 'bottom top',
      scrub: 1
    }
  });

  // Organic rows animation
  gsap.utils.toArray('.organic-row').forEach(row => {
    const isReverse = row.classList.contains('reverse');
    const textBlock = row.querySelector('.text-block');
    const imageBlock = row.querySelector('.image-block');
    const textStartX = isReverse ? 50 : -50;
    const imageStartX = isReverse ? -50 : 50;

    gsap.from(textBlock.children, {
      x: textStartX, opacity: 0, duration: 0.8, stagger: 0.1, ease: 'power3.out',
      scrollTrigger: { trigger: row, start: 'top 85%', end: 'bottom 15%', toggleActions: 'play reverse play reverse' }
    });

    gsap.from(imageBlock, {
      x: imageStartX, opacity: 0, duration: 0.9, ease: 'power3.out',
      scrollTrigger: { trigger: row, start: 'top 85%', end: 'bottom 15%', toggleActions: 'play reverse play reverse' }
    });
  });

  // Parallax for showcase
  gsap.utils.toArray('.text-block').forEach(block => {
    gsap.to(block, {
      y: -25, ease: 'none',
      scrollTrigger: { trigger: block, start: 'top bottom', end: 'bottom top', scrub: true }
    });
  });

  gsap.utils.toArray('.image-block').forEach(block => {
    gsap.to(block, {
      y: -40, ease: 'none',
      scrollTrigger: { trigger: block, start: 'top bottom', end: 'bottom top', scrub: true }
    });
  });

  // Process line draw
  const processLine = document.querySelector('.process-line-draw');
  if (processLine) {
    gsap.to(processLine, {
      strokeDashoffset: 0, ease: 'none',
      scrollTrigger: { trigger: '.process-grid', start: 'top 70%', end: 'bottom 60%', scrub: true }
    });
  }

  // Horizontal pinned gallery
  if (galleryTrack) {
    ScrollTrigger.matchMedia({
      "(min-width: 901px)": function () {
        let getScrollAmount = () => galleryTrack.scrollWidth - window.innerWidth;
        
        gsap.to(galleryTrack, {
          x: () => -getScrollAmount(),
          ease: 'none',
          scrollTrigger: {
            trigger: '.gallery-section',
            start: 'center center',
            end: () => `+=${getScrollAmount() * 2}`, // Multiplied by 2 to slow down the animation
            scrub: 1,
            pin: true,
            anticipatePin: 1,
            invalidateOnRefresh: true
          }
        });
      }
    });
  }

  // Fade up animations for lower sections
  const fadeUpElements = gsap.utils.toArray('.section-head, .about-visual, .team-card, .testimonial-card, .feature-tile, .faq-item, .pricing-card');
  fadeUpElements.forEach(el => {
    gsap.from(el, {
      y: 40,
      opacity: 0,
      duration: 0.8,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: el,
        start: 'top 85%',
        end: 'bottom 15%',
        toggleActions: 'play reverse play reverse'
      }
    });
  });

  // Fluid grid (capabilities) items animation from left and right
  const fluidItems = gsap.utils.toArray('.fluid-item');
  if (fluidItems.length > 0) {
    fluidItems.forEach((item, i) => {
      // Alternate animation direction: even index from left, odd from right
      const xOffset = i % 2 === 0 ? -80 : 80;
      gsap.from(item, {
        x: xOffset,
        opacity: 0,
        duration: 0.9,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: item,
          start: 'top 85%',
          end: 'bottom 15%',
          toggleActions: 'play reverse play reverse'
        }
      });
    });
  }

  // ========== SPLIT-TEXT REVEAL ==========
  function splitTextWords(element) {
    const text = element.innerText;
    const words = text.trim().split(/\s+/);
    element.innerHTML = '';
    words.forEach(word => {
      const outer = document.createElement('span');
      outer.style.overflow = 'hidden';
      outer.style.display = 'inline-block';
      outer.style.verticalAlign = 'bottom';
      
      const inner = document.createElement('span');
      inner.classList.add('split-word-inner');
      inner.style.display = 'inline-block';
      inner.innerHTML = word + '&nbsp;';
      
      outer.appendChild(inner);
      element.appendChild(outer);
    });
  }

  gsap.utils.toArray('h2').forEach(h2 => {
    if (h2.children.length === 0) {
      splitTextWords(h2);
      gsap.from(h2.querySelectorAll('.split-word-inner'), {
        scrollTrigger: {
          trigger: h2,
          start: 'top 90%',
          toggleActions: 'play reverse play reverse'
        },
        yPercent: 110,
        opacity: 0,
        duration: 0.8,
        stagger: 0.05,
        ease: 'power3.out'
      });
    }
  });

  // ========== SCROLL-REACTIVE MARQUEE ==========
  const marqueeTrackEle = document.querySelector('.marquee-track');
  if (marqueeTrackEle) {
    marqueeTrackEle.style.animation = 'none';
    const marqueeTween = gsap.to(marqueeTrackEle, {
      xPercent: -50,
      ease: "none",
      duration: 20,
      repeat: -1
    });

    ScrollTrigger.create({
      trigger: document.body,
      start: "top top",
      end: "bottom bottom",
      onUpdate: (self) => {
        let velocity = self.getVelocity();
        let ts = 1 + (velocity / 500); 
        gsap.to(marqueeTween, { timeScale: ts, duration: 0.5, overwrite: true });
        gsap.to(marqueeTween, { timeScale: 1, duration: 1, delay: 0.2, overwrite: false });
      }
    });
  }

  // ========== SCROLL-DRIVEN BACKGROUND COLOR SHIFT ==========
  const showcaseSection = document.querySelector('#showcase');
  if (showcaseSection) {
    const bgColors = ['#F5F5F0', '#F0F4F8', '#F2F0F5', '#F8F2F0'];
    const defaultBg = '#FAFAF7';
    
    gsap.utils.toArray('.organic-row').forEach((row, i) => {
      ScrollTrigger.create({
        trigger: row,
        start: "top center",
        end: "bottom center",
        onEnter: () => gsap.to("body", { backgroundColor: bgColors[i % bgColors.length], duration: 0.8, overwrite: "auto" }),
        onEnterBack: () => gsap.to("body", { backgroundColor: bgColors[i % bgColors.length], duration: 0.8, overwrite: "auto" })
      });
    });
    
    ScrollTrigger.create({
      trigger: showcaseSection,
      start: "top center",
      end: "bottom center",
      onLeave: () => gsap.to("body", { backgroundColor: defaultBg, duration: 0.8, overwrite: "auto" }),
      onLeaveBack: () => gsap.to("body", { backgroundColor: defaultBg, duration: 0.8, overwrite: "auto" })
    });
  }

  // Refresh on load
  window.addEventListener('load', () => {
    ScrollTrigger.refresh();
  });

  // ========== CREATIVE FOOTER INTERACTIONS ==========
  const footer = document.querySelector('.footer');
  const glassCard = document.querySelector('.newsletter.glass-card');

  if (footer && glassCard) {
    footer.addEventListener('mousemove', (e) => {
      const rect = footer.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      // 1. Spotlight Effect
      footer.style.setProperty('--mouseX', `${x}px`);
      footer.style.setProperty('--mouseY', `${y}px`);
    });

    // 3. 3D Tilt on Glass Card
    glassCard.addEventListener('mousemove', (e) => {
      const cardRect = glassCard.getBoundingClientRect();
      const cardX = e.clientX - cardRect.left;
      const cardY = e.clientY - cardRect.top;
      const centerX = cardRect.width / 2;
      const centerY = cardRect.height / 2;
      
      const rotateX = ((cardY - centerY) / centerY) * -10; // max 10 deg
      const rotateY = ((cardX - centerX) / centerX) * 10;
      
      glassCard.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
      glassCard.style.boxShadow = `${-rotateY}px ${rotateX}px 40px rgba(56, 189, 248, 0.25), ${rotateY}px ${-rotateX}px 40px rgba(239, 68, 68, 0.25)`;
    });

    glassCard.addEventListener('mouseleave', () => {
      glassCard.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
      glassCard.style.boxShadow = `-20px -20px 60px rgba(56, 189, 248, 0.15), 20px 20px 60px rgba(239, 68, 68, 0.15)`;
    });
    
    footer.addEventListener('mouseleave', () => {
      footer.style.setProperty('--mouseX', `50%`);
      footer.style.setProperty('--mouseY', `50%`);
    });
  }

  // ========== FOOTER ENTRANCE ANIMATION ==========
  if (document.querySelector('.footer')) {
    gsap.from(".footer-brand > *, .footer-col", {
      scrollTrigger: {
        trigger: ".footer",
        start: "top 95%",
        end: "bottom 5%",
        toggleActions: "play reverse play reverse"
      },
      y: 40,
      opacity: 0,
      duration: 0.8,
      stagger: 0.1,
      ease: "power3.out"
    });
  }
}

// ========== MOBILE TOUCH ENHANCEMENTS ==========
if ('ontouchstart' in window) {
  document.querySelectorAll('.fluid-item, .gallery-item').forEach(item => {
    item.addEventListener('touchstart', function () {
      this.classList.add('touch-active');
    });
    item.addEventListener('touchend', function () {
      setTimeout(() => {
        this.classList.remove('touch-active');
      }, 300);
    });
  });
}
