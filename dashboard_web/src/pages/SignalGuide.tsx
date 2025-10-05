import { ExternalLinkIcon } from "../ui/ExternalLinkIcon";

const resources = {
  danZanger: "https://www.investopedia.com/terms/c/cupandhandle.asp",
  canSlim: "https://www.investopedia.com/terms/c/canslim.asp",
  trendFollowing: "https://www.investopedia.com/articles/trading/08/trend-trading.asp",
  livermore: "https://www.investopedia.com/articles/trading/09/jesse-livermore.asp",
  positionSizing: "https://www.investopedia.com/terms/p/positionsizing.asp",
  riskReward: "https://www.investopedia.com/terms/r/riskrewardratio.asp",
  volume: "https://www.investopedia.com/terms/v/volume.asp",
};

const signalBlocks = [
  {
    title: "Dan Zanger Cup & Handle",
    summary:
      "Looks for rounded cup bases followed by a tight handle before a high-volume breakout above resistance.",
    whatToWatch: [
      "Cup depth between 12% and 35% with a strong recovery toward prior highs",
      "Handle drift stays relatively shallow (5-15%) and tight in price range",
      "Breakout must occur on decisive volume, ideally 1.5x the 20-day average",
    ],
    whatToAvoid: [
      "Handles that undercut the midpoint of the cup",
      "Breakouts without a volume surge or with wide, volatile candles",
      "Cup structures that form too quickly (under 8 weeks) or drag on longer than 6 months",
    ],
    linkLabel: "Cup-and-handle primer",
    link: resources.danZanger,
  },
  {
    title: "CAN SLIM Score",
    summary:
      "Composite score derived from earnings growth, relative strength, proximity to 52-week highs, and volume expansion.",
    whatToWatch: [
      "Earnings growth at or above 25% with consistent results year over year",
      "Relative strength above 0.8 indicates top-quintile outperformance",
      "Price close to its 52-week high while volume expands versus average",
    ],
    whatToAvoid: [
      "Rising score driven by a single factor while others deteriorate",
      "Volume spikes accompanied by falling price (distribution days)",
      "Companies with erratic earnings growth or recurring one-off gains",
    ],
    linkLabel: "CAN SLIM overview",
    link: resources.canSlim,
  },
  {
    title: "EMA Trend Following",
    summary:
      "Tracks short- and long-term exponential moving averages plus ATR-based stops to capture sustained trends.",
    whatToWatch: [
      "Fast EMA crossing above slow EMA with price respecting the fast EMA as support",
      "ATR-based stop distance shrinking as volatility contracts",
      "Multiple time frame alignment (for example, weekly trend also pointing higher)",
    ],
    whatToAvoid: [
      "Whipsaw environments with frequent crossovers",
      "Taking signals without price closing above the fast EMA",
      "Ignoring rising ATR readings, which widen stops and signal volatility spikes",
    ],
    linkLabel: "Trend trading basics",
    link: resources.trendFollowing,
  },
  {
    title: "Livermore Breakout",
    summary:
      "Identifies tight consolidations (Livermore's \"pivotal points\") followed by volume-backed breakouts.",
    whatToWatch: [
      "Range contraction over 3-5 weeks (no more than ~15% high-to-low)",
      "Breakout candle closing near the high with 1.3x average volume",
      "Sector leadership or healthy market breadth when the breakout triggers",
    ],
    whatToAvoid: [
      "Breakouts triggered during weak overall market breadth",
      "Loose bases where intraday ranges stay wide",
      "Volume dry-ups that fail to reverse prior selling pressure",
    ],
    linkLabel: "Livermore's trading approach",
    link: resources.livermore,
  },
  {
    title: "Aggregated Signal",
    summary:
      "Weighted blend of all strategies. Reinforces when multiple playbooks align and filters out isolated signals.",
    whatToWatch: [
      "Clustered BUY signals across at least two playbooks",
      "Confidence above 0.6 combined with rising relative strength",
      "Review backtest stats (win rate, expectancy) for the specific symbol or universe",
    ],
    whatToAvoid: [
      "Aggregation driven by a single high-confidence outlier",
      "Conflicting signals (BUY and SELL) firing within a short window",
      "Chasing signals far above the breakout or after extended gaps",
    ],
    linkLabel: "Position sizing & risk management",
    link: resources.positionSizing,
  },
];

export function SignalGuide() {
  return (
    <div className="mx-auto w-full max-w-4xl space-y-12 px-4 pb-20 pt-10">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold text-slate-900">Signal Interpretation Guide</h1>
        <p className="text-base text-slate-600">
          Use this as a quick reference when assessing signals surfaced by the dashboard. Each section highlights what a
          constructive setup looks like, when to be cautious, and where to deepen your understanding.
        </p>
      </header>

      <div className="grid gap-8">
        {signalBlocks.map((block) => (
          <section key={block.title} className="rounded-3xl border border-slate-200 bg-white/95 p-8 shadow-sm shadow-slate-200/60">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-semibold text-slate-900">{block.title}</h2>
                <p className="mt-2 text-base text-slate-600">{block.summary}</p>
              </div>
              <a
                href={block.link}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-full border border-blue-400/40 bg-blue-50 px-3 py-1 text-sm font-medium text-blue-700 transition hover:border-blue-500 hover:bg-blue-100"
              >
                {block.linkLabel}
                <ExternalLinkIcon />
              </a>
            </div>

            <div className="mt-6 grid gap-6 md:grid-cols-2">
              <div className="rounded-2xl bg-emerald-50/80 p-6">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-emerald-600">What to look for</h3>
                <ul className="mt-3 space-y-2 text-sm text-emerald-800">
                  {block.whatToWatch.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="mt-1 inline-block h-2 w-2 rounded-full bg-emerald-500" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-2xl bg-rose-50/80 p-6">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-rose-600">Caution signs</h3>
                <ul className="mt-3 space-y-2 text-sm text-rose-800">
                  {block.whatToAvoid.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="mt-1 inline-block h-2 w-2 rounded-full bg-rose-500" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
