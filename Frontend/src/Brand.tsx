import emblem from './assets/volga-tech-seal.png'

export function Brand({ showEmblem = false }: { showEmblem?: boolean }) {
  return <span className="brand">Volga<b>Ask</b>
    {showEmblem && <img className="brand-emblem" src={emblem} alt="VolgaTech" />}
  </span>
}
