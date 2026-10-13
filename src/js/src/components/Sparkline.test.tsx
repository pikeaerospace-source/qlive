/**
 * Tests for the inline SVG sparkline.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Sparkline from "./Sparkline";

const line = () => document.querySelector(".sparkline__line") as SVGElement;
const points = () =>
  (line().getAttribute("points") ?? "").trim().split(/\s+/).filter(Boolean);

describe("Sparkline", () => {
  it("renders nothing for an empty series", () => {
    const { container } = render(<Sparkline values={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("plots one point per value, scaled to the series max", () => {
    render(<Sparkline values={[0, 10]} width={100} height={50} />);

    expect(points()).toEqual(["0.0,50.0", "100.0,0.0"]);
  });

  it("flattens a single-sample series into a full-width line", () => {
    render(<Sparkline values={[5]} width={100} height={50} />);

    expect(points()).toEqual(["0,0.0", "100,0.0"]);
  });

  it("keeps a flat series off the baseline when the values are non-zero", () => {
    // max == every value → the line sits at the top (y = 0).
    render(<Sparkline values={[7, 7]} width={100} height={50} />);

    expect(points()).toEqual(["0.0,0.0", "100.0,0.0"]);
  });

  it("exposes an accessible image with the given label", () => {
    render(<Sparkline values={[1, 2, 3]} label="Bandwidth over time" />);

    expect(
      screen.getByRole("img", { name: "Bandwidth over time" }),
    ).toBeInTheDocument();
  });
});
