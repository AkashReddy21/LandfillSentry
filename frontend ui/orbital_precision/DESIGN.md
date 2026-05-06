---
name: Orbital Precision
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#bdc8d1'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#87929a'
  outline-variant: '#3e484f'
  surface-tint: '#7bd0ff'
  primary: '#8ed5ff'
  on-primary: '#00354a'
  primary-container: '#38bdf8'
  on-primary-container: '#004965'
  inverse-primary: '#00668a'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#ffc174'
  on-tertiary: '#472a00'
  tertiary-container: '#f59e0b'
  on-tertiary-container: '#613b00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#c4e7ff'
  primary-fixed-dim: '#7bd0ff'
  on-primary-fixed: '#001e2c'
  on-primary-fixed-variant: '#004c69'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  display-lg:
    fontFamily: Space Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: 0.01em
  data-mono:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.05em
  body-base:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.04em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 16px
  margin: 24px
  panel-padding: 20px
  stack-sm: 8px
  stack-md: 16px
---

## Brand & Style

This design system is engineered for high-stakes operational environments where speed of comprehension and technical accuracy are paramount. The visual language evokes a "Mission Control" aesthetic—utilitarian, sophisticated, and vigilant. It prioritizes the clear display of geospatial data and satellite telemetry over decorative elements.

The style is a blend of **Minimalism** and **Modern Corporate**, utilizing a dark-first philosophy to reduce eye strain during long-duration monitoring. Elements are defined by structural integrity and precision, using subtle borders and high-contrast status indicators to guide the operator's eye to critical anomalies. The emotional response is one of calm authority, ensuring users feel in total control of complex, planetary-scale data.

## Colors

The palette is optimized for low-light environments. The primary color is a high-visibility Sky Blue, representing satellite connectivity and atmosphere. The neutral scale is rooted in deep Slates and Navies to provide a receded background for vibrant data overlays.

Functional colors are non-negotiable and follow international safety standards:
- **Safety Green:** Indicates normal sensor readings and "all-clear" status.
- **Alert Amber:** Indicates methane fluctuations or sensor drift requiring attention.
- **Critical Red:** Reserved for significant leak detections and system failures.

Data visualization should use a secondary palette of cold cyans and purples to distinguish satellite imagery filters from operational UI elements.

## Typography

This design system utilizes a dual-font strategy to balance technical character with extreme legibility. 

**Space Grotesk** is used for headlines, telemetry readouts, and key data points. Its geometric, technical quirks reinforce the high-tech, aerospace nature of the tool. 

**Inter** is the workhorse for body copy, structured reporting, and interface labels. It provides the neutral, systematic clarity required for reading dense tables and incident logs. For coordinate data and timestamps, utilize Inter with tabular lining figures to ensure vertical alignment in data columns.

## Layout & Spacing

The layout employs a **Fluid Grid** system designed for 16:9 widescreen displays common in operational hubs. A 12-column system handles the primary dashboard content, while persistent sidebars for "Active Alerts" and "Toolbox" sit outside the primary grid on fixed-width rails.

Spacing follows a strict 4px base unit. Density is high by default—"Operational Density"—to minimize scrolling and keep all vital metrics within the primary viewport. Components should use generous internal padding to maintain legibility, but margins between dashboard widgets are kept tight (16px) to maximize screen real estate for geospatial maps.

## Elevation & Depth

In a mission-critical dark UI, shadows are avoided to prevent visual "muddiness." Instead, hierarchy is established through **Tonal Layering** and **Low-Contrast Outlines**.

1.  **Floor (Level 0):** Deepest Navy (#020617), used for the map background and global canvas.
2.  **Panels (Level 1):** Slate (#0F172A) with a 1px border (#334155). These house standard data widgets.
3.  **Overlays (Level 2):** Floating map controls or modals use a lighter Slate (#1E293B) with a subtle primary-tinted glow or 1px border to indicate they are "above" the data.

Interactivity is signaled by "inner-light" effects—active states use a subtle inner stroke of the primary color rather than a drop shadow.

## Shapes

The shape language is "Functional Sharp." A 4px (Soft) radius is applied to most components to provide a modern feel without sacrificing the professional, "engineered" look. 

- **Buttons & Inputs:** 4px radius.
- **Status Badges:** 2px radius (near-sharp) to distinguish them as technical tags.
- **Data Containers:** 4px radius.
- **Map Selection Tools:** 0px (Sharp) to emphasize mathematical precision.

Avoid large-scale rounding or circular elements unless they represent literal circular data (like sensor radius or orbital paths).

## Components

### Buttons & Inputs
Buttons are high-contrast blocks. Primary buttons use solid fills, while secondary actions use "Ghost" styles with 1px borders. Input fields must include clear unit suffixes (e.g., "ppm", "kg/h") within the field box to prevent data entry errors.

### Status Chips
Status chips are the most vibrant elements in the UI. They use a "filled-edge" style: a dark background with a thick 3px left-border of the status color (Green/Amber/Red) to ensure the status is identifiable even in peripheral vision.

### Data Visualization Widgets
Charts should be "sparkline" style for historical trends, stripping away non-essential axes. Use high-contrast line weights. For geospatial imagery, provide "Crosshair" components that snap to grid coordinates.

### Incident Reporting Cards
These cards use a structured, three-section layout:
1.  **Header:** ID Number, Timestamp, and Status Badge.
2.  **Body:** Snapshot of the methane plume and coordinate data.
3.  **Footer:** Action buttons (Acknowledge, Escalate, Export).

### Telemetry Lists
Dense, monospaced lists for real-time sensor feeds. Use alternating row highlights (Zebra striping) with very low contrast change for maximum readability of large data sets.