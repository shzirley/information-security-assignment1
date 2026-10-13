export function BrandLogo({ tagline = false, stacked = false, inverse = false }: { tagline?: boolean; stacked?: boolean; inverse?: boolean }) {
  return <span className={`brand-logo ${stacked ? 'brand-logo-stacked' : ''} ${inverse ? 'brand-logo-inverse' : ''}`}>
    <img src="/brand/veltrix-symbol.svg" alt="" aria-hidden="true" width="44" height="44" className="brand-symbol" />
    <span className="brand-type"><span className="brand-wordmark">VELTRIX</span>{tagline && <span className="brand-tagline" aria-hidden="true">Your data. Your control.</span>}</span>
  </span>;
}
