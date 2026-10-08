// The ready-made prompts in the composer's "/" menu, by category. A picked prompt is inserted into the
// message as written, so each one reads as a complete request the builder can act on, in plain words.
export type PromptCategory =
    "Accessibility" | "SEO" | "Usability" | "Performance" | "General" | "Workflow";

interface Prompt {
    category: PromptCategory;
    name: string;
    prompt: string;
}

export const PROMPTS: Prompt[] = [
    {
        category: "Accessibility",
        name: "Check accessibility",
        prompt: "Check this app for accessibility problems and fix them, most serious first: form fields without labels, images without alt text, text with too little contrast, places the keyboard gets stuck, missing focus outlines, a broken heading order and vague link text.",
    },
    {
        category: "Accessibility",
        name: "Keyboard and focus",
        prompt: "Make every part of the app usable with the keyboard alone. Show a clear focus outline on everything that can be focused, keep it from being hidden behind sticky headers, keep focus inside open dialogs and return it to where it was when they close.",
    },
    {
        category: "Accessibility",
        name: "Label icon buttons",
        prompt: "Give every button and link that shows only an icon a clear name for screen readers, and hide purely decorative icons from them.",
    },
    {
        category: "Accessibility",
        name: "Don't rely on color",
        prompt: "Find every place where color alone carries meaning, such as errors, statuses or required fields, and add text or an icon so it still makes sense without color.",
    },
    {
        category: "Accessibility",
        name: "Respect reduced motion",
        prompt: "When the visitor's device asks for reduced motion, tone down or remove animations, and add a pause control to anything that keeps moving for more than five seconds.",
    },
    {
        category: "SEO",
        name: "SEO essentials",
        prompt: "Add search-engine basics to every page: a unique, descriptive title, a meta description, a canonical link and a single main heading with a logical heading order underneath it.",
    },
    {
        category: "SEO",
        name: "Social share previews",
        prompt: "Add social sharing tags with a title, description, image and link to every page, so links look good when they are shared.",
    },
    {
        category: "SEO",
        name: "Sitemap and robots",
        prompt: "Add a robots.txt that allows search engines to crawl the site and a sitemap.xml that lists every public page, with clear, readable page addresses.",
    },
    {
        category: "SEO",
        name: "Structured data",
        prompt: "Add structured data that describes this site to search engines, such as the organization, website, products or articles, using only what is actually shown on each page.",
    },
    {
        category: "SEO",
        name: "Image SEO",
        prompt: "Give every meaningful image a descriptive alt text and a descriptive file name, and mark purely decorative images so they are skipped.",
    },
    {
        category: "Usability",
        name: "Improve layout",
        prompt: "Improve the layout and spacing of this app so it feels balanced, consistent and easy to scan.",
    },
    {
        category: "Usability",
        name: "Empty, loading and error states",
        prompt: "Give every screen and list a proper empty state, loading state and error state, and make sure no screen is a dead end: each one offers a next step or a way to recover.",
    },
    {
        category: "Usability",
        name: "Better forms",
        prompt: "Improve every form: a visible label on each field, the right keyboard on phones, autofill where it helps, errors shown next to the field they belong to, focus on the first error after submitting, and a warning before leaving with unsaved changes.",
    },
    {
        category: "Usability",
        name: "Mobile friendly",
        prompt: "Make the app comfortable on phones: buttons and links at least 44px tall, text inputs that don't make the phone zoom in, content clear of the notch and home bar, and nothing that only works on hover.",
    },
    {
        category: "Usability",
        name: "Confirm before deleting",
        prompt: "Make every destructive action, such as delete, remove or reset, either ask for confirmation first or offer an undo for a few seconds afterwards.",
    },
    {
        category: "Usability",
        name: "Clearer messages",
        prompt: "Rewrite error and empty-state messages so they say what happened and how to fix it in plain, friendly words, and replace vague button labels like Continue or Submit with what the button actually does.",
    },
    {
        category: "Usability",
        name: "Remember where I was",
        prompt: "Keep filters, tabs, search and pagination in the page address, so refreshing, sharing a link or going back keeps the visitor's place.",
    },
    {
        category: "Performance",
        name: "Speed up loading",
        prompt: "Make the app load faster: show the main content first, reserve space for images and embeds so the page doesn't jump while loading, and keep clicks and typing responsive.",
    },
    {
        category: "Performance",
        name: "Optimize images",
        prompt: "Optimize every image: modern formats, sizes that fit the screen, explicit width and height, the main image loaded first and images further down the page loaded only when they are needed.",
    },
    {
        category: "Performance",
        name: "Lighter app",
        prompt: "Make the app lighter: load heavy screens and components only when they are opened, remove unused packages and load non-essential third-party scripts last.",
    },
    {
        category: "Performance",
        name: "Faster fonts",
        prompt: "Load fonts efficiently so text appears straight away in a fallback font and swaps in without the page jumping.",
    },
    {
        category: "Performance",
        name: "Smooth long lists",
        prompt: "Keep long lists and busy screens smooth: only render what is on screen, avoid needless re-rendering and animate only movement and fading.",
    },
    {
        category: "General",
        name: "Dark mode",
        prompt: "Add a dark mode that follows the device setting, with a toggle to switch it by hand that is remembered, and check that text stays readable in both themes.",
    },
    {
        category: "General",
        name: "Error handling",
        prompt: "Handle errors gracefully: if part of the app crashes, show a friendly message with a way to try again instead of a blank screen, and fix any errors the app currently logs.",
    },
    {
        category: "General",
        name: "Local dates and numbers",
        prompt: "Show dates, times, numbers and prices in the visitor's own language and format.",
    },
    {
        category: "General",
        name: "Installable app",
        prompt: "Make the app installable on phones and computers: add an app name, icons and theme colors, and let it open full screen from the home screen.",
    },
    {
        category: "General",
        name: "Friendly 404 page",
        prompt: "Add a friendly page-not-found screen that matches the app's design and offers a clear way back to the main pages.",
    },
    {
        category: "Workflow",
        name: "Fix an issue",
        prompt: "Fix this issue in my app:",
    },
    {
        category: "Workflow",
        name: "Explain the code",
        prompt: "Explain how the current app works: its main screens, how data moves through it and where each feature lives.",
    },
    {
        category: "Workflow",
        name: "Suggest improvements",
        prompt: "Don't change anything yet. Review the app's structure, design consistency and user experience, then list the five improvements that would help most, in order of impact.",
    },
    {
        category: "Workflow",
        name: "Clean up the code",
        prompt: "Tidy up the code so it is easier to maintain, without changing how the app looks or behaves.",
    },
    {
        category: "Workflow",
        name: "Write a README",
        prompt: "Write a clear README for this project: what it does, how to run it and how it is organized.",
    },
];
