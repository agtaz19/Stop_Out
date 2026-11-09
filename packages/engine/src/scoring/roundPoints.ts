/**
 * Round performance points (component A, 500 points by default).
 * Each round is worth totalPoints / rounds, scaled by the fund's percentile.
 */
export function roundPoints(
  percentilesByRound: readonly number[],
  rounds = percentilesByRound.length,
  totalPoints = 500,
): number {
  if (rounds <= 0) throw new RangeError("rounds must be positive");
  const perRound = totalPoints / rounds;
  return percentilesByRound.reduce((sum, p) => sum + perRound * p, 0);
}
