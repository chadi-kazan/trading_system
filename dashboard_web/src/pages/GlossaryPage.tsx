const glossaryEntries = [
  {
    term: "ATR (Average True Range)",
    definition: "A volatility indicator measuring the degree of price movement over a specified period.",
    link: "https://www.investopedia.com/terms/a/atr.asp",
  },
  {
    term: "Breakout",
    definition: "A price move outside a consolidation or resistance/support zone, often confirmed with volume.",
    link: "https://www.investopedia.com/terms/b/breakout.asp",
  },
  {
    term: "CAN SLIM",
    definition: "A growth investing framework emphasizing earnings, new products, and market leadership.",
    link: "https://www.investopedia.com/terms/c/canslim.asp",
  },
  {
    term: "Cup and Handle",
    definition: "A bullish continuation pattern where price forms a rounded base (cup) followed by a small pullback (handle).",
    link: "https://www.investopedia.com/terms/c/cupandhandle.asp",
  },
  {
    term: "EMA (Exponential Moving Average)",
    definition: "A moving average that assigns more weight to recent data points, reacting faster to price changes.",
    link: "https://www.investopedia.com/terms/e/ema.asp",
  },
  {
    term: "Relative Strength",
    definition: "A measure comparing a stock's performance vs. a benchmark or peer group.",
    link: "https://www.investopedia.com/terms/r/relativestrength.asp",
  },
  {
    term: "Volume Dry-Up",
    definition: "A period where trading volume contracts significantly, often preceding a decisive move.",
    link: "https://www.investopedia.com/terms/v/volume.asp",
  },
  {
    term: "Risk/Reward",
    definition: "Framework evaluating potential upside vs. downside before entering a trade.",
    link: "https://www.investopedia.com/terms/r/riskrewardratio.asp",
  },
];

export function GlossaryPage() {
  return (
    <div className="mx-auto w-full max-w-3xl space-y-8 px-4 pb-20 pt-10">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold text-slate-900">Glossary & Abbreviations</h1>
        <p className="text-base text-slate-600">
          Expand any term below to reveal a plain-language explanation and jump to an external primer if you're learning the
          concepts for the first time.
        </p>
      </header>

      <div className="space-y-4">
        {glossaryEntries.map((entry) => (
          <details key={entry.term} className="rounded-2xl border border-slate-200 bg-white/95 p-5 shadow-sm shadow-slate-200/60">
            <summary className="cursor-pointer text-lg font-semibold text-slate-900">
              {entry.term}
            </summary>
            <p className="mt-3 text-sm text-slate-600">{entry.definition}</p>
            <a
              href={entry.link}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-blue-600 transition hover:text-blue-500"
            >
              Learn more on Investopedia
              <span aria-hidden className="h-4 w-4">?</span>
            </a>
          </details>
        ))}
      </div>
    </div>
  );
}
