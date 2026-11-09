import { describe, expect, it } from "vitest";
import {
  intervalScore,
  percentileRanks,
  roundPoints,
  shrunkInformationRatio,
} from "../src/index.ts";

// Cases come from the worked examples in the Stop-Out design spec.

describe("intervalScore", () => {
  it("scores a 30bp interval that contains the outcome at its width", () => {
    expect(intervalScore(0, 30, 15)).toBe(30);
  });

  it("charges ten times each basis point of miss at alpha = 0.2", () => {
    expect(intervalScore(0, 30, 40)).toBe(130);
    expect(intervalScore(0, 30, -10)).toBe(130);
  });

  it("rejects an inverted interval", () => {
    expect(() => intervalScore(30, 0, 15)).toThrow(RangeError);
  });
});

describe("percentileRanks", () => {
  it("gives the best fund 1 and the worst 0", () => {
    expect(percentileRanks([3, 1, 2])).toEqual([1, 0, 0.5]);
  });

  it("averages tied ranks", () => {
    // Ranks 1, 2.5, 2.5, 4 among four funds.
    expect(percentileRanks([5, 3, 3, 1])).toEqual([1, 0.5, 0.5, 0]);
  });

  it("supports lower-is-better metrics such as the interval score", () => {
    expect(percentileRanks([130, 30, 80], false)).toEqual([0, 1, 0.5]);
  });

  it("handles a field of one", () => {
    expect(percentileRanks([42])).toEqual([1]);
  });
});

describe("roundPoints", () => {
  it("matches the all-in desk: 1st in four rounds, 10th in four", () => {
    expect(roundPoints([1, 0, 1, 0, 1, 0, 1, 0])).toBe(250);
  });

  it("matches the steady desk: 3rd of 10 every round", () => {
    const p = 7 / 9;
    expect(roundPoints(Array(8).fill(p))).toBeCloseTo(388.89, 2);
  });

  it("keeps the 500-point total in a six-round session", () => {
    expect(roundPoints(Array(6).fill(1))).toBeCloseTo(500, 10);
  });
});

describe("shrunkInformationRatio", () => {
  it("matches the spec example: mean 0.30, s = 0.20, s0 = 0.25", () => {
    // Two-point series with mean 0.30 and sample sd 0.20.
    const e = [0.3 - 0.2 / Math.SQRT2, 0.3 + 0.2 / Math.SQRT2];
    expect(shrunkInformationRatio(e)).toBeCloseTo(0.937, 3);
  });

  it("does not explode for a fund that sits in cash", () => {
    expect(shrunkInformationRatio([0.01, 0.01, 0.01])).toBeCloseTo(0.04, 10);
  });
});
