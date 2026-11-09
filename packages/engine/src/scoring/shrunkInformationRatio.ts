/**
 * Shrunk information ratio over a fund's normalized round excess returns:
 *
 *   IR* = mean(e) / sqrt(s^2 + s0^2)
 *
 * s is the sample standard deviation (n - 1 denominator; 0 for one round).
 * The floor s0 stops a fund that sits in cash from posting an enormous
 * ratio on a tiny standard deviation.
 */
export function shrunkInformationRatio(
  normalizedExcess: readonly number[],
  s0 = 0.25,
): number {
  const n = normalizedExcess.length;
  if (n === 0) throw new RangeError("need at least one round");
  const mean = normalizedExcess.reduce((a, b) => a + b, 0) / n;
  const variance =
    n > 1
      ? normalizedExcess.reduce((a, b) => a + (b - mean) ** 2, 0) / (n - 1)
      : 0;
  return mean / Math.sqrt(variance + s0 * s0);
}
