/**
 * Sector pictogram icons for the map.
 *
 * Each sector renders as a small white industry pictogram inside the marker's
 * coloured circle background. Icons are registered as SDF images so MapLibre's
 * `icon-color` paint property can tint them (always white in our case, but SDF
 * also gives crisp scaling at any zoom).
 *
 * The same SVG path data is exported for the legend so the on-map icon and
 * the legend swatch are bit-identical — no shape drift between the two.
 */

import type { Sector } from './siteTypes';

/** Offscreen canvas size for SDF rasterization (retina-ready). */
export const SECTOR_ICON_CANVAS_PX = 64;

/** Source SVG viewBox the path data is authored against. */
const ICON_VIEWBOX = 24;

/** MapLibre image name for a given sector. */
export function sectorIconName(sector: Sector): string {
  return `sector-icon-${sector}`;
}

/**
 * SVG path data per sector (24x24 viewBox). Authored to be visually distinct
 * silhouettes that read clearly even at ~12px on screen. Anything more
 * detailed gets lost on a continental zoom.
 *
 * mixed   = SEZ/KEK industrial-park skyline (mixed-height buildings)
 * cement  = kiln silos with crossbar
 * steel   = stepped anvil / ingot pyramid
 * aluminium = stacked LME-style ingot pyramid
 * nickel  = factory with sawtooth roof
 * fertilizer = sack with shoulder bevel ("Pupuk" bag)
 * ammonia = round-bottom chemistry flask
 * petrochemical = stepped distillation column
 */
export const SECTOR_ICON_PATHS: Record<Sector, string> = {
  mixed: 'M3 21h18v-2H3v2zM5 18h2V8H5v10zm4 0h2V5H9v13zm4 0h2v-8h-2v8zm4 0h2v-6h-2v6z',
  cement: 'M4 20h16v-6H4v6zm2-14h2v6H6V6zm4 0h4v6h-4V6zm6 0h2v6h-2V6zM5 4h14v1H5V4z',
  steel: 'M2 18h20v2H2v-2zm1-2h18l-2-4H5L3 16zm4-6h10v2H7v-2zm2-4h6v2H9V6z',
  aluminium: 'M4 18h16v3H4v-3zm2-3h12v3H6v-3zm2-3h8v3H8v-3zm2-3h4v3h-4V9zm1-3h2v3h-2V6z',
  nickel: 'M2 20V9l6-3v3l4-2v3l4-2v3l6-3v12H2z',
  fertilizer: 'M7 4h10v2l-1 1v12c0 1-1 2-2 2H10c-1 0-2-1-2-2V7L7 6V4z',
  ammonia: 'M10 3h4v3l3 8v3c0 1-1 2-2 2H9c-1 0-2-1-2-2v-3l3-8V3z',
  petrochemical: 'M9 3h6v3H9V3zm-1 4h8v3H8V7zm-2 4h12v10H6V11z',
};

/** Short human label of what the pictogram depicts (used in the legend tooltip). */
export const SECTOR_SHAPE_LABELS: Record<Sector, string> = {
  mixed: 'Skyline',
  cement: 'Kiln',
  steel: 'Anvil',
  aluminium: 'Ingots',
  nickel: 'Factory',
  fertilizer: 'Sack',
  ammonia: 'Flask',
  petrochemical: 'Column',
};

/**
 * Rasterize the sector pictogram to ImageData suitable for `addImage({sdf:true})`.
 * Solid white alpha-mask of the SVG path; MapLibre recolors via `icon-color`.
 */
export function createSectorIconImageData(sector: Sector): ImageData {
  const size = SECTOR_ICON_CANVAS_PX;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('2D context unavailable');

  ctx.clearRect(0, 0, size, size);
  ctx.fillStyle = '#ffffff';

  // Leave a small margin so the path doesn't clip when MapLibre samples the SDF.
  const margin = 4;
  const scale = (size - 2 * margin) / ICON_VIEWBOX;
  ctx.save();
  ctx.translate(margin, margin);
  ctx.scale(scale, scale);
  const path = new Path2D(SECTOR_ICON_PATHS[sector]);
  ctx.fill(path);
  ctx.restore();

  return ctx.getImageData(0, 0, size, size);
}

/**
 * Register every sector icon on the given MapLibre map instance.
 * Safe to call repeatedly — existing images are skipped.
 */
export function registerSectorIcons(map: maplibregl.Map): void {
  const sectors: Sector[] = [
    'mixed',
    'cement',
    'steel',
    'aluminium',
    'nickel',
    'fertilizer',
    'ammonia',
    'petrochemical',
  ];
  for (const sector of sectors) {
    const name = sectorIconName(sector);
    if (map.hasImage(name)) continue;
    const imageData = createSectorIconImageData(sector);
    map.addImage(name, imageData, { sdf: true });
  }
}
