import type { JSX } from "react";
import type { SavedSignal, WatchlistStatus } from "../hooks/useWatchlist";
import { IndexMomentumPage } from "./IndexMomentumPage";
import { fetchSpMomentum } from "../api";

type SPMomentumPageProps = {
  watchlistItems: SavedSignal[];
  onSaveWatchlist: (symbol: string, status: WatchlistStatus) => Promise<unknown>;
};

export function SPMomentumPage({
  watchlistItems,
  onSaveWatchlist,
}: SPMomentumPageProps): JSX.Element {
  return (
    <IndexMomentumPage
      title="S&P 500 Momentum"
      description="Screen S&P 500 constituents for broad-market momentum, review strategy alignment, and fast-track names into the central watchlist."
      fetchMomentum={fetchSpMomentum}
      watchlistItems={watchlistItems}
      onSaveWatchlist={onSaveWatchlist}
      indexKey="S&P 500"
    />
  );
}

export default SPMomentumPage;
