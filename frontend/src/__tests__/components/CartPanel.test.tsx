import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CartPanel } from "../../components/CartPanel";
import type { CartEntry } from "../../hooks/useCart";
import type { RecipeListItem } from "../../types";

function makeEntry(
  id: number,
  title: string,
  servings: number
): CartEntry {
  const recipe: RecipeListItem = {
    id,
    title,
    url: `https://example.com/${id}`,
    source_domain: "example.com",
    image_local_path: null,
    base_servings: servings,
    prep_time_minutes: null,
    is_favorite: false,
    tags: [],
  };
  return { recipe, target_servings: servings };
}

describe("CartPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  // ── Empty state ────────────────────────────────────────────────────────────
  it("shows empty-state message when cart is empty", () => {
    render(
      <CartPanel
        cart={[]}
        onUpdateServings={vi.fn()}
        onClearCart={vi.fn()}
        onGenerateList={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(screen.getByText("cart.empty")).toBeInTheDocument();
  });

  it("disables Clear button when cart is empty", () => {
    render(
      <CartPanel
        cart={[]}
        onUpdateServings={vi.fn()}
        onClearCart={vi.fn()}
        onGenerateList={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(screen.getByText("cart.clear").closest("button")).toBeDisabled();
  });

  it("disables Generate List button when cart is empty", () => {
    render(
      <CartPanel
        cart={[]}
        onUpdateServings={vi.fn()}
        onClearCart={vi.fn()}
        onGenerateList={vi.fn().mockResolvedValue(undefined)}
      />
    );
    // The generate button's text key is used to find it
    // Find the second button (generate)
    const buttons = screen.getAllByRole("button");
    // Clear button + Generate button are the action buttons; both disabled
    const disabledButtons = buttons.filter((b) => b.hasAttribute("disabled"));
    expect(disabledButtons.length).toBeGreaterThanOrEqual(2);
  });

  // ── Non-empty state ────────────────────────────────────────────────────────
  it("renders recipe titles for each cart entry", () => {
    const cart = [
      makeEntry(1, "Pasta Bolognese", 4),
      makeEntry(2, "Chocolate Cake", 8),
    ];
    render(
      <CartPanel
        cart={cart}
        onUpdateServings={vi.fn()}
        onClearCart={vi.fn()}
        onGenerateList={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(screen.getByText("Pasta Bolognese")).toBeInTheDocument();
    expect(screen.getByText("Chocolate Cake")).toBeInTheDocument();
  });

  it("displays current serving count for each entry", () => {
    const cart = [makeEntry(1, "Soup", 3)];
    render(
      <CartPanel
        cart={cart}
        onUpdateServings={vi.fn()}
        onClearCart={vi.fn()}
        onGenerateList={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("decrease button is disabled when servings = 1", () => {
    const cart = [makeEntry(1, "Recipe", 1)];
    render(
      <CartPanel
        cart={cart}
        onUpdateServings={vi.fn()}
        onClearCart={vi.fn()}
        onGenerateList={vi.fn().mockResolvedValue(undefined)}
      />
    );
    const decreaseBtn = screen.getByLabelText("cart.decreaseServings");
    expect(decreaseBtn).toBeDisabled();
  });

  it("decrease button is enabled when servings > 1", () => {
    const cart = [makeEntry(1, "Recipe", 2)];
    render(
      <CartPanel
        cart={cart}
        onUpdateServings={vi.fn()}
        onClearCart={vi.fn()}
        onGenerateList={vi.fn().mockResolvedValue(undefined)}
      />
    );
    const decreaseBtn = screen.getByLabelText("cart.decreaseServings");
    expect(decreaseBtn).not.toBeDisabled();
  });

  it("clicking decrease calls onUpdateServings with current - 1", () => {
    const onUpdateServings = vi.fn();
    const cart = [makeEntry(1, "Recipe", 4)];
    render(
      <CartPanel
        cart={cart}
        onUpdateServings={onUpdateServings}
        onClearCart={vi.fn()}
        onGenerateList={vi.fn().mockResolvedValue(undefined)}
      />
    );
    fireEvent.click(screen.getByLabelText("cart.decreaseServings"));
    expect(onUpdateServings).toHaveBeenCalledWith(1, 3);
  });

  it("clicking increase calls onUpdateServings with current + 1", () => {
    const onUpdateServings = vi.fn();
    const cart = [makeEntry(1, "Recipe", 2)];
    render(
      <CartPanel
        cart={cart}
        onUpdateServings={onUpdateServings}
        onClearCart={vi.fn()}
        onGenerateList={vi.fn().mockResolvedValue(undefined)}
      />
    );
    fireEvent.click(screen.getByLabelText("cart.increaseServings"));
    expect(onUpdateServings).toHaveBeenCalledWith(1, 3);
  });

  it("clicking Clear calls onClearCart", () => {
    const onClearCart = vi.fn();
    const cart = [makeEntry(1, "Recipe", 2)];
    render(
      <CartPanel
        cart={cart}
        onUpdateServings={vi.fn()}
        onClearCart={onClearCart}
        onGenerateList={vi.fn().mockResolvedValue(undefined)}
      />
    );
    fireEvent.click(screen.getByText("cart.clear").closest("button")!);
    expect(onClearCart).toHaveBeenCalledOnce();
  });
});
