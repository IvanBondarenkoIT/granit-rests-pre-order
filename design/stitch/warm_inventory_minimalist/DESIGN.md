---
name: Warm Inventory Minimalist
colors:
  surface: '#fcf9f5'
  surface-dim: '#dcdad6'
  surface-bright: '#fcf9f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3ef'
  surface-container: '#f0ede9'
  surface-container-high: '#ebe8e4'
  surface-container-highest: '#e5e2de'
  on-surface: '#1c1c1a'
  on-surface-variant: '#50453e'
  inverse-surface: '#31302e'
  inverse-on-surface: '#f3f0ec'
  outline: '#82746d'
  outline-variant: '#d4c3ba'
  surface-tint: '#79573f'
  primary: '#553722'
  on-primary: '#ffffff'
  primary-container: '#6f4e37'
  on-primary-container: '#eec1a4'
  inverse-primary: '#eabda0'
  secondary: '#875208'
  on-secondary: '#ffffff'
  secondary-container: '#ffb869'
  on-secondary-container: '#784700'
  tertiary: '#004923'
  on-tertiary: '#ffffff'
  tertiary-container: '#006332'
  on-tertiary-container: '#75e096'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdcc6'
  primary-fixed-dim: '#eabda0'
  on-primary-fixed: '#2d1604'
  on-primary-fixed-variant: '#5f402a'
  secondary-fixed: '#ffdcbb'
  secondary-fixed-dim: '#ffb869'
  on-secondary-fixed: '#2c1700'
  on-secondary-fixed-variant: '#673d00'
  tertiary-fixed: '#8df9ac'
  tertiary-fixed-dim: '#71dc92'
  on-tertiary-fixed: '#00210d'
  on-tertiary-fixed-variant: '#005229'
  background: '#fcf9f5'
  on-background: '#1c1c1a'
  surface-variant: '#e5e2de'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-rg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  data-tabular:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-margin: 20px
  gutter: 16px
  card-padding: 20px
  stack-gap-sm: 8px
  stack-gap-md: 16px
  stack-gap-lg: 24px
---

## Brand & Style
The design system is centered on a "Sophisticated Brew" aesthetic—balancing the industrial precision of inventory management with the warmth of a premium coffee house. The target audience includes cafe managers and baristas who require a high-utility tool that feels calm and approachable during high-stress shifts.

The style is a blend of **Minimalism** and **Tactile Modernism**. It uses expansive whitespace (airy layout), high-quality typography, and soft, organic depth. The UI avoids clutter, prioritizing legibility and ease of interaction through large touch targets and a clear visual hierarchy. The emotional response should be one of "controlled focus"—reducing the cognitive load of data tracking through a warm, inviting interface.

## Colors
The palette is inspired by the roasting process. The primary **Espresso Brown** provides grounding and authority, used for key actions and headers. **Caramel** acts as a secondary accent for highlights and interactive sub-elements.

The background uses a warm off-white to reduce eye strain compared to pure white, creating a "paper-like" feel. Status colors are calibrated for high visibility against the warm neutrals, ensuring that critical stock levels are immediately identifiable. In Dark Mode, the background shifts to a deep roasted bean tone (#1B1714) with elevated surfaces using subtle desaturated shifts of the primary palette.

## Typography
This design system utilizes **Inter** for its exceptional legibility and modern, neutral character. To handle the inventory aspect of the application, **JetBrains Mono** (or Inter with Tabular Figures enabled) is used specifically for stock counts, prices, and timestamps to ensure vertical alignment in lists and tables.

Large headings should use tighter letter spacing to maintain a "graphic" feel. Body text maintains standard spacing for maximum readability. All Cyrillic characters must respect the same weight and height standards as the Latin set to ensure a premium feel in the Russian language interface.

## Layout & Spacing
The layout follows a **Fluid Grid** model with a base unit of 8px. 

- **Mobile:** A single-column layout with 20px side margins. Elements are stacked vertically with a 16px or 24px gap.
- **Tablet/Desktop:** A 12-column grid. Cards can span 4, 6, or 12 columns depending on the data density (e.g., small "Quick Stats" span 4, while "Inventory Lists" span 12).

The "Airy" feel is achieved by using generous internal padding within cards (20px) and ensuring that the vertical rhythm never feels cramped. Navigation is anchored to a fixed bottom bar on mobile to keep primary actions within reach of the thumb.

## Elevation & Depth
Hierarchy is established through **Ambient Shadows** and **Tonal Layering**. 

1. **Base Layer:** The warm background (#F7F4F0).
2. **Surface Layer (Cards):** Pure white (#FFFFFF) with a very soft, diffused shadow (0px 4px 20px rgba(111, 78, 55, 0.08)). The shadow uses a hint of the Primary Espresso color to maintain warmth.
3. **Active/Overlay Layer:** Elevated elements (modals/drawers) use a slightly stronger shadow and a 1px soft border (#6F4E37 at 5% opacity) to define edges without harshness.

Avoid using heavy black shadows. All depth should feel "sun-drenched" and soft.

## Shapes
The shape language is "Friendly Professional." 

- **Cards & Containers:** Use `rounded-lg` (16px) to create a soft, modern container.
- **Buttons & Inputs:** Use `rounded-md` (8px) for a slightly more structured look that suggests interactability.
- **Progress Bars:** Fully rounded (pill-shaped) to represent fluid movement and modern data visualization.
- **Interactive States:** Use a subtle 4px corner radius for hover/focus states on list items.

## Components

### Buttons
- **Primary:** Espresso Brown background, white text, 8px radius.
- **Secondary:** Caramel background, white text.
- **Ghost:** No background, Espresso Brown text, used for less frequent actions like "Add Note."

### Cards
Cards are the primary organizational unit. They must have a white background, 16px corner radius, and the standard ambient shadow. Headers inside cards should use `headline-md`.

### Progress Bars
Used for stock levels. The track should be a very light tint of the status color (15% opacity), and the indicator should be the solid status color (OK, Warning, or Critical).

### Bottom Navigation
A fixed 3-item bar:
1. **Склад** (Inventory/Warehouse)
2. **Заказы** (Orders)
3. **Отчеты** (Reports)
Use 24px stroke-based icons with a 2pt weight. The active state uses the Caramel color for both icon and label.

### Input Fields
Soft-filled fields using a 5% opacity version of Espresso Brown. On focus, the border transitions to a 2px Caramel stroke. Labels are positioned above the field using `label-caps`.

### Simple Charts
Line and Bar charts should use the Primary and Secondary accent colors. Grid lines should be minimal, using #E8E2DA to stay secondary to the data.