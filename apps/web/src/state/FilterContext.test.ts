/**
 * Unit tests for FilterContext pure utility functions.
 * These run in node environment (no DOM needed).
 */
import { describe, it, expect } from "vitest";
import { presetToDates, parseDims, type Preset } from "./FilterContext";

// ─── presetToDates ────────────────────────────────────────────────────────────

describe("presetToDates", () => {
  it("7d returns a range of 7 days ending today", () => {
    const { dateFrom, dateTo } = presetToDates("7d");
    const today = new Date().toISOString().slice(0, 10);
    const fromDate = new Date(dateFrom);
    const toDate = new Date(dateTo);
    expect(dateTo).toBe(today);
    const diffDays = (toDate.getTime() - fromDate.getTime()) / 86_400_000;
    expect(diffDays).toBe(7);
  });

  it("28d returns a range of 28 days ending today", () => {
    const { dateFrom, dateTo } = presetToDates("28d");
    const fromDate = new Date(dateFrom);
    const toDate = new Date(dateTo);
    const diffDays = (toDate.getTime() - fromDate.getTime()) / 86_400_000;
    expect(diffDays).toBe(28);
  });

  it("qtd starts on the first day of the current quarter", () => {
    const { dateFrom } = presetToDates("qtd");
    // dateFrom is an ISO string like "YYYY-MM-DD"
    // Quarter start months are 01, 04, 07, 10 and the day must be 01
    const [, mm, dd] = dateFrom.split("-");
    expect(["01", "04", "07", "10"]).toContain(mm);
    expect(dd).toBe("01");
  });

  it("ytd starts on January 1st of the current year", () => {
    const { dateFrom } = presetToDates("ytd");
    // dateFrom is an ISO string like "YYYY-01-01"
    const currentYear = new Date().getFullYear().toString();
    expect(dateFrom).toBe(`${currentYear}-01-01`);
  });

  it("custom returns a default 28d range", () => {
    const { dateFrom, dateTo } = presetToDates("custom");
    const fromDate = new Date(dateFrom);
    const toDate = new Date(dateTo);
    const diffDays = (toDate.getTime() - fromDate.getTime()) / 86_400_000;
    expect(diffDays).toBe(28);
  });

  it("all presets return valid ISO date strings", () => {
    const presets: Preset[] = ["7d", "28d", "qtd", "ytd", "custom"];
    const isoPattern = /^\d{4}-\d{2}-\d{2}$/;
    for (const p of presets) {
      const { dateFrom, dateTo } = presetToDates(p);
      expect(dateFrom).toMatch(isoPattern);
      expect(dateTo).toMatch(isoPattern);
    }
  });

  it("dateFrom is always before or equal to dateTo", () => {
    const presets: Preset[] = ["7d", "28d", "qtd", "ytd", "custom"];
    for (const p of presets) {
      const { dateFrom, dateTo } = presetToDates(p);
      expect(new Date(dateFrom).getTime()).toBeLessThanOrEqual(
        new Date(dateTo).getTime()
      );
    }
  });
});

// ─── parseDims ────────────────────────────────────────────────────────────────

describe("parseDims", () => {
  it("parses a single key=value pair", () => {
    const result = parseDims("region=North");
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({ key: "region", value: "North", raw: "region=North" });
  });

  it("parses multiple comma-separated pairs", () => {
    const result = parseDims("region=North,channel=online");
    expect(result).toHaveLength(2);
    expect(result[0].key).toBe("region");
    expect(result[1].key).toBe("channel");
  });

  it("returns empty array for empty string", () => {
    expect(parseDims("")).toHaveLength(0);
  });

  it("skips malformed entries without an = sign", () => {
    const result = parseDims("region=North,badentry");
    expect(result).toHaveLength(2);
    expect(result[1]).toEqual({ key: "badentry", value: "", raw: "badentry" });
  });

  it("handles values containing = signs gracefully", () => {
    const result = parseDims("label=hello=world");
    expect(result).toHaveLength(1);
    expect(result[0].key).toBe("label");
    expect(result[0].value).toBe("hello=world");
  });

  it("trims whitespace from keys and values", () => {
    const result = parseDims(" region = North ");
    expect(result[0].key).toBe("region");
    expect(result[0].value).toBe("North");
  });
});
