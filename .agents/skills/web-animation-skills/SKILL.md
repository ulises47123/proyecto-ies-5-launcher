---
name: web-animation-skills
description: >-
  Expert guide for modern web animations, UI transitions, 60fps GPU acceleration,
  micro-interactions, and smooth web interface state progressions.
---

# Web Animation & Transition Skills Guide

This skill provides best practices, patterns, and guidelines for designing high-performance, fluid, and non-blocking web animations for modern web interfaces.

---

## 1. Core Principles of Web Animation

1. **Performant Properties (Composite-Only)**:
   - Animate ONLY `transform` (scale, translate, rotate) and `opacity`.
   - Avoid animating layout properties (`width`, `height`, `margin`, `padding`, `top`, `left`) to prevent browser reflows (layout thrashing).
   - Use `will-change: transform, opacity` sparingly on elements with complex continuous animations.

2. **Smooth Timing & Easing Functions**:
   - Use cubic-bezier easing functions for natural motion:
     - `cubic-bezier(0.4, 0, 0.2, 1)` (standard ease-in-out)
     - `cubic-bezier(0, 0, 0.2, 1)` (deceleration / entrance)
     - `cubic-bezier(0.4, 0, 1, 1)` (acceleration / exit)
   - Keep interaction animations under 300ms for crisp responsiveness.

3. **Preventing Flicker & Compositing Issues**:
   - Avoid combining heavy `backdrop-filter: blur(...)` with rapid keypresses or frequent DOM re-renders inside input fields.
   - Use hardware acceleration (`transform: translateZ(0)` or `backface-visibility: hidden`) for fixed overlays and modals.

---

## 2. Micro-Interactions & UI Components

### Modal Entrance / Exit
```css
.modal-overlay {
  transition: opacity 0.2s cubic-bezier(0, 0, 0.2, 1);
}
.modal-content {
  transition: transform 0.25s cubic-bezier(0, 0, 0.2, 1), opacity 0.25s ease;
  transform: scale(0.95) translateY(8px);
}
.modal-open .modal-content {
  transform: scale(1) translateY(0);
  opacity: 1;
}
```

### Loading Spinners & Skeleton Waves
```css
@keyframes skeleton-shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
.skeleton-loader {
  background: linear-gradient(90deg, #1b2a47 25%, #2d3f63 50%, #1b2a47 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite linear;
}
```

---

## 3. Tailwind CSS Animation Patterns

- **Smooth Hover Lift**: `transition-all duration-200 ease-out hover:-translate-y-0.5 hover:shadow-lg`
- **Fade Entrance**: `transition-opacity duration-300 ease-in-out`
- **Pulse Accent**: `animate-pulse` for soft background indicators.
