import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import MessageBubble from "./MessageBubble";
import type { ShipmentOut } from "../../api/secureship";

const shipment: ShipmentOut = {
  id: "ship-1",
  tracking_number: "940086518506716572",
  status: "in_transit",
  carrier: "USPS",
  origin: "San Francisco, CA",
  destination: "Dallas, TX",
  estimated_delivery: "2026-10-02",
  last_update: "2026-02-05T12:00:00+00:00",
  packages: [
    { description: "Power Tools", weight_kg: 14.557, declared_value: 876.79 },
    {
      description: "Camera Equipment",
      weight_kg: 17.815,
      declared_value: 651.39,
    },
  ],
};

describe("MessageBubble", () => {
  it("renders a shipment card from the structured payload", () => {
    render(
      <MessageBubble
        role="assistant"
        content="Here are the details."
        shipments={[shipment]}
      />,
    );

    expect(screen.getByText("940086518506716572")).toBeInTheDocument();
    expect(screen.getByText("USPS")).toBeInTheDocument();
    expect(screen.getByText("San Francisco, CA")).toBeInTheDocument();
    expect(screen.getByText("Dallas, TX")).toBeInTheDocument();
    expect(screen.getByText("In Transit")).toBeInTheDocument();
    expect(screen.getByText("Here are the details.")).toBeInTheDocument();
  });

  it("formats dates without shifting across time zones", () => {
    render(
      <MessageBubble role="assistant" content="" shipments={[shipment]} />,
    );

    expect(screen.getByText("October 2, 2026")).toBeInTheDocument();
    expect(screen.getByText("February 5, 2026")).toBeInTheDocument();
  });

  it("renders the packages table when packages are present", () => {
    render(
      <MessageBubble role="assistant" content="" shipments={[shipment]} />,
    );

    expect(screen.getByText("Packages (2)")).toBeInTheDocument();
    expect(screen.getByText("Power Tools")).toBeInTheDocument();
    expect(screen.getByText("14.557 kg")).toBeInTheDocument();
    expect(screen.getByText("$876.79")).toBeInTheDocument();
    expect(screen.getByText("Camera Equipment")).toBeInTheDocument();
  });

  it("omits the packages section for list results that carry no packages", () => {
    render(
      <MessageBubble
        role="assistant"
        content=""
        shipments={[{ ...shipment, packages: null }]}
      />,
    );

    expect(screen.getByText("940086518506716572")).toBeInTheDocument();
    expect(screen.queryByText(/^Packages/)).not.toBeInTheDocument();
  });

  it("renders one card per shipment", () => {
    const second = {
      ...shipment,
      id: "ship-2",
      tracking_number: "123456789012",
    };
    render(
      <MessageBubble
        role="assistant"
        content=""
        shipments={[shipment, second]}
      />,
    );

    expect(screen.getAllByText("Tracking")).toHaveLength(2);
    expect(screen.getByText("123456789012")).toBeInTheDocument();
  });

  it("falls back to a plain markdown bubble when there is no payload", () => {
    render(<MessageBubble role="assistant" content="Hello **there**" />);

    expect(screen.getByText("there")).toBeInTheDocument();
    expect(screen.queryByText("Tracking")).not.toBeInTheDocument();
  });

  it("shows a dash when last_update is missing", () => {
    render(
      <MessageBubble
        role="assistant"
        content=""
        shipments={[{ ...shipment, last_update: null }]}
      />,
    );

    expect(screen.getByText("\u2014")).toBeInTheDocument();
  });

  it("falls back to the default style for an unknown status", () => {
    render(
      <MessageBubble
        role="assistant"
        content=""
        shipments={[{ ...shipment, status: "bogus" }]}
      />,
    );

    expect(screen.getByText("Label Created")).toBeInTheDocument();
  });
});
