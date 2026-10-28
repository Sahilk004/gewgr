import { describe, expect, it } from "vitest";
import { describeAge, fmtMW, fmtPct, fmtSigned } from "./format";

describe("format", () => {
  it("formats MW and handles missing values", () => {
    expect(fmtMW(1234.4)).toBe("1,234 MW");
    expect(fmtMW(null)).toBe("–");
  });
  it("signs bias", () => {
    expect(fmtSigned(150)).toBe("+150 MW");
    expect(fmtSigned(-150)).toBe("-150 MW");
  });
  it("formats percent", () => expect(fmtPct(12.345)).toBe("12.3%"));
  it("describes forecast age", () => {
    expect(describeAge(0.5)).toBe("30 min");
    expect(describeAge(2)).toBe("2 h");
    expect(describeAge(2.25)).toBe("2 h 15 min");
  });
});
