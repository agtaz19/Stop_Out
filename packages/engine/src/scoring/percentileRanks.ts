/**
 * Percentile rank of each value among all values, in [0, 1].
 *
 * Rank k = 1 is the best value. Tied values share the average of the ranks
 * they span (two funds tied for 2nd both get rank 2.5). The percentile is
 * p = (N - k) / (N - 1), so the best fund scores 1 and the worst 0.
 * A field of one fund scores 1.
 */
export function percentileRanks(
  values: readonly number[],
  higherIsBetter = true,
): number[] {
  const n = values.length;
  if (n === 0) return [];
  if (values.some((v) => !Number.isFinite(v))) {
    throw new RangeError("percentileRanks requires finite values");
  }
  if (n === 1) return [1];

  const order = values
    .map((value, index) => ({ value, index }))
    .sort((a, b) => (higherIsBetter ? b.value - a.value : a.value - b.value));

  const ranks = new Array<number>(n);
  let i = 0;
  while (i < n) {
    let j = i;
    while (j + 1 < n && order[j + 1]!.value === order[i]!.value) j += 1;
    const averageRank = (i + 1 + (j + 1)) / 2;
    for (let t = i; t <= j; t += 1) ranks[order[t]!.index] = averageRank;
    i = j + 1;
  }
  return ranks.map((k) => (n - k) / (n - 1));
}
