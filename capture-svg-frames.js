const puppeteer = require('puppeteer');
const path = require('path');


// Get the SVG path from command-line arguments
const svgPathArg = process.argv[2]; // The third element in process.argv is the first argument

if (!svgPathArg) {
    console.error('Please provide the path to the SVG file as a command-line argument.');
    process.exit(1);
}

// Resolve the SVG path to handle relative paths
const svgPath = path.resolve(svgPathArg);

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();

    // Set viewport size to control the size of the captured frame
    await page.setViewport({
        width: 1100,  // Width of the viewport
        height: 640  // Height of the viewport
    });

    // Correctly resolve the path to the SVG file
    //const svgPath = 'file:///e:/Desktop/test_py/downloaded_svgs/embedded_svg_1.svg';

    // Load the SVG file
    await page.goto(svgPath);

    // Change the viewBox attribute of the SVG
    const viewBox = '0 0 550 320'; // Adjust these values as needed
    await page.evaluate((viewBox) => {
        const svgElement = document.querySelector('svg');
        if (svgElement) {
            console.log(`Original viewBox: ${svgElement.getAttribute('viewBox')}`);
            svgElement.setAttribute('viewBox', viewBox);
            console.log(`Updated viewBox: ${svgElement.getAttribute('viewBox')}`);
        } else {
            console.error('SVG element not found');
        }
    }, viewBox);

    // Number of frames to capture
    const numberOfFrames = 35;
    var delay = 2;

    for (let i = 0; i < numberOfFrames; i++) {
        // Wait for 850ms before capturing the frame
        await new Promise(resolve => setTimeout(resolve, delay));

        // Capture the screenshot of the SVG with adjusted clipping area
        await page.screenshot({
            path: `downloaded_svgs/frames/frame_${i + 1}.png`,
            clip: {
                x: 0,                     // X-coordinate of the clipping area
                y: 0,                     // Y-coordinate of the clipping area
                width: 1100,               // Width of the clipping area
                height: 640               // Height of the clipping area
            }
        });
        //console.log(`Captured frame ${i + 1}`);
    }

    await browser.close();
})();
