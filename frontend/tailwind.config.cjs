module.exports = {
  darkMode: 'class',
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      screens: {
        nav: "777px",
      },
      colors: {
        base: "#fdfdfc",
        paper: "#faf8f5",
        ink: "#1f2937",
        accent: "#00a859",
      },
      fontFamily: {
        heading: ["Poppins", "sans-serif"],
        body: ["Manrope", "sans-serif"],
      },
    },
  },
  plugins: [],
};
