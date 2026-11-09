/**
 * Interval score for a central (1 - alpha) forecast interval [lower, upper]
 * against the realized outcome (Gneiting and Raftery, 2007). Lower is better.
 *
 * All inputs share one unit; the game uses basis points of 10y yield.
 * With alpha = 0.2 (an 80% interval), every basis point of miss costs
 * 2 / alpha = 10 times a basis point of width.
 */
export function intervalScore(
  lower: number,
  upper: number,
  outcome: number,
  alpha = 0.2,
): number {
  if (!(alpha > 0 && alpha < 1)) {
    throw new RangeError(`alpha must be in (0, 1), got ${alpha}`);
  }
  if (upper < lower) {
    throw new RangeError(`upper (${upper}) is below lower (${lower})`);
  }
  const width = upper - lower;
  const below = outcome < lower ? (2 / alpha) * (lower - outcome) : 0;
  const above = outcome > upper ? (2 / alpha) * (outcome - upper) : 0;
  return width + below + above;
}
