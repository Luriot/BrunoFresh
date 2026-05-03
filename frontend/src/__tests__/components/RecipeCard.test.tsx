import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { RecipeCard } from "../../components/RecipeCard";
import type { RecipeListItem } from "../../types";

// Mock the API client so tests don't make real HTTP requests.
vi.mock("../../api/client", () => ({
  buildImageUrl: (path: string) => `/images/${path}`,
  patchRecipe: vi.fn(),
}));

import { patchRecipe } from "../../api/client";
const mockPatchRecipe = vi.mocked(patchRecipe);

function makeRecipe(overrides: Partial<RecipeListItem> = {}): RecipeListItem {
  return {
    id: 1,
    title: "Spaghetti Bolognese",
    url: "https://example.com/recipe",
    source_domain: "example.com",
    image_local_path: null,
    base_servings: 4,
    prep_time_minutes: 30,
    is_favorite: false,
    tags: [],
    ...overrides,
  };
}

describe("RecipeCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the recipe title", () => {
    render(
      <RecipeCard
        recipe={makeRecipe()}
        onAdd={vi.fn()}
      />
    );
    expect(screen.getByText("Spaghetti Bolognese")).toBeInTheDocument();
  });

  it("renders the source domain", () => {
    render(
      <RecipeCard
        recipe={makeRecipe()}
        onAdd={vi.fn()}
      />
    );
    expect(screen.getByText("example.com")).toBeInTheDocument();
  });

  it("shows no-image placeholder when image_local_path is null", () => {
    render(
      <RecipeCard
        recipe={makeRecipe({ image_local_path: null })}
        onAdd={vi.fn()}
      />
    );
    expect(screen.getByText("recipe.noImage")).toBeInTheDocument();
  });

  it("renders an img element when image_local_path is provided", () => {
    render(
      <RecipeCard
        recipe={makeRecipe({ image_local_path: "recipe-1.jpg" })}
        onAdd={vi.fn()}
      />
    );
    const img = screen.getByRole("img", { name: "Spaghetti Bolognese" });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "/images/recipe-1.jpg");
  });

  it("calls onAdd with the recipe when the add-to-cart button is clicked", () => {
    const onAdd = vi.fn();
    const recipe = makeRecipe();
    render(<RecipeCard recipe={recipe} onAdd={onAdd} />);

    fireEvent.click(screen.getByText("recipe.addToCart"));
    expect(onAdd).toHaveBeenCalledOnce();
    expect(onAdd).toHaveBeenCalledWith(recipe);
  });

  it("calls onClick when the card article is clicked", () => {
    const onClick = vi.fn();
    render(
      <RecipeCard recipe={makeRecipe()} onAdd={vi.fn()} onClick={onClick} />
    );
    // Click the article container (the card itself)
    fireEvent.click(screen.getByRole("article"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("calls onFavoriteToggled with updated recipe after favorite toggle", async () => {
    const updated = makeRecipe({ is_favorite: true });
    mockPatchRecipe.mockResolvedValueOnce(updated as never);
    const onFavoriteToggled = vi.fn();

    render(
      <RecipeCard
        recipe={makeRecipe({ is_favorite: false })}
        onAdd={vi.fn()}
        onFavoriteToggled={onFavoriteToggled}
      />
    );

    fireEvent.click(screen.getByLabelText("recipe.favorite"));
    await waitFor(() => expect(onFavoriteToggled).toHaveBeenCalledOnce());
    expect(onFavoriteToggled).toHaveBeenCalledWith(expect.objectContaining({ is_favorite: true }));
  });
});
