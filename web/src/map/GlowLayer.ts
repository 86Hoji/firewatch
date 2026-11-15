import { ScatterplotLayer } from '@deck.gl/layers';

/** A ScatterplotLayer whose discs fade from the centre: soft halos that add up where fires cluster. */
export class GlowLayer<D> extends ScatterplotLayer<D> {
  static layerName = 'GlowLayer';
  getShaders() {
    const s = super.getShaders();
    return {
      ...s,
      inject: {
        ...(s.inject || {}),
        'fs:DECKGL_FILTER_COLOR': `
          float d = clamp(length(geometry.uv), 0.0, 1.0);
          float k = 1.0 - d;
          color.a *= k * k * k;
        `,
      },
    };
  }
}
