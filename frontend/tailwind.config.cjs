module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#f8f6ee",
        ink: "#1f2937",
        accent: "#dd6b20",
      },
      fontFamily: {
        heading: ["Poppins", "sans-serif"],
        body: ["Manrope", "sans-serif"],
      },
    },
  },
  plugins: [],
};
