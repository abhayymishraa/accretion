// Libraries.dev effects that are installed but switched off. Each waits on something the product does
// not have yet; flip the flag once it does. While off, their modules (three.js included) never load.
export const EFFECTS = {
    // img-fx: a WebGL pixel mosaic that resolves into real images. Needs preview screenshots
    // published to the client; with no image there is nothing for the mosaic to resolve into.
    previewImageReveal: false,
    // liquid-gooey: the composer's @ and / buttons melt out of one another. Needs an expanding
    // tool tray for them to move in; side by side and still, there is nothing to merge.
    liquidComposerTools: false,
} as const;
