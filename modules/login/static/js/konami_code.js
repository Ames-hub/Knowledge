// Konami Code reference lol
const code = [
  "ArrowUp","ArrowUp","ArrowDown","ArrowDown",
  "ArrowLeft","ArrowRight","ArrowLeft","ArrowRight",
  "b","a"
];

let i = 0;

window.addEventListener("keydown", e => {
  if (e.key === code[i]) {
    i++;
    if (i === code.length) {
      triggerKonamiEffect();
      i = 0;
    }
  } else {
    i = 0;
  }
});

// Dramatic Konami Code effect
function triggerKonamiEffect() {
  // Create overlay
  const overlay = document.createElement('div');
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(45deg, #ff006e, #8338ec, #3a86ff, #06ffa5);
    background-size: 400% 400%;
    z-index: 9999;
    display: flex;
    justify-content: center;
    align-items: center;
    animation: gradientShift 2s ease-in-out;
  `;
  
  // Create text
  const text = document.createElement('div');
  text.style.cssText = `
    font-size: 120px;
    font-weight: bold;
    color: white;
    text-shadow: 0 0 20px rgba(255,255,255,0.8);
    animation: pulseScale 0.6s cubic-bezier(0.36, 0, 0.66, -0.56);
    z-index: 10000;
  `;
  text.textContent = '🎉 LEGEND MODE UNLOCKED 🎉';
  
  overlay.appendChild(text);
  document.body.appendChild(overlay);
  
  // Create particle effects
  for (let j = 0; j < 30; j++) {
    const particle = document.createElement('div');
    const size = Math.random() * 20 + 10;
    particle.style.cssText = `
      position: fixed;
      width: ${size}px;
      height: ${size}px;
      background: ${['#ff006e', '#8338ec', '#3a86ff', '#06ffa5', '#ffbe0b'][Math.floor(Math.random() * 5)]};
      border-radius: 50%;
      pointer-events: none;
      z-index: 9998;
      top: 50%;
      left: 50%;
      animation: particleExplode 1.5s ease-out forwards;
      animation-delay: ${j * 0.05}s;
    `;
    document.body.appendChild(particle);
  }
  
  // Remove effects after animation
  setTimeout(() => {
    overlay.remove();
    document.querySelectorAll('div[style*="particleExplode"]').forEach(el => el.remove());
  }, 2000);
}

// Add keyframe animations to stylesheet
const style = document.createElement('style');
style.textContent = `
  @keyframes gradientShift {
    0% { background-position: 0% 50%; opacity: 1; }
    100% { background-position: 100% 50%; opacity: 0; }
  }
  
  @keyframes pulseScale {
    0% { transform: scale(0); opacity: 0; }
    50% { transform: scale(1.2); opacity: 1; }
    100% { transform: scale(1); opacity: 1; }
  }
  
  @keyframes particleExplode {
    0% {
      transform: translate(0, 0) scale(1);
      opacity: 1;
    }
    100% {
      transform: translate(
        calc(cos(var(--angle)) * 400px),
        calc(sin(var(--angle)) * 400px)
      ) scale(0);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);
