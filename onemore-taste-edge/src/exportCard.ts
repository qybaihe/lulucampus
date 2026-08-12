import { toCanvas } from "html-to-image";

/** Snapshot a card and paint Lulu back on — html-to-image often drops the footer sprite. */
export async function exportNodePng(node: HTMLElement): Promise<string> {
  const lulu = node.querySelector<HTMLImageElement>("img.lulu-still");
  if (lulu && (!lulu.complete || lulu.naturalWidth === 0)) {
    await new Promise<void>((resolve) => {
      const done = () => resolve();
      lulu.onload = done;
      lulu.onerror = done;
      window.setTimeout(done, 1200);
    });
  }

  const prevVisibility = lulu?.style.visibility;
  if (lulu) lulu.style.visibility = "hidden";
  try {
    const canvas = await toCanvas(node, {
      cacheBust: false,
      pixelRatio: 2,
      backgroundColor: "#fffaf0",
      skipFonts: false,
    });
    if (lulu && lulu.naturalWidth > 0) {
      const ctx = canvas.getContext("2d");
      if (ctx) {
        const nodeRect = node.getBoundingClientRect();
        const imgRect = lulu.getBoundingClientRect();
        const sx = canvas.width / nodeRect.width;
        const sy = canvas.height / nodeRect.height;
        ctx.drawImage(
          lulu,
          (imgRect.left - nodeRect.left) * sx,
          (imgRect.top - nodeRect.top) * sy,
          imgRect.width * sx,
          imgRect.height * sy,
        );
      }
    }
    return canvas.toDataURL("image/png");
  } finally {
    if (lulu) lulu.style.visibility = prevVisibility || "";
  }
}
