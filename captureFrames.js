const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function captureFrames(url, outputDir) {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });
    
    const page = await browser.newPage();

    //console.log(url, outputDir)

    // Go to the provided URL
    await page.goto(url);

    // Add background color to the SVG element
    await page.evaluate(() => {
        const svg = document.querySelector('svg');
        if (svg) {
            svg.style.backgroundColor = '#262626';
        }
    });

    // Select SVG elements
    const svgElement = await page.$('svg'); // Modify selector if needed

    // Check if the output directory exists; create if not
    if (!fs.existsSync(outputDir)){
        fs.mkdirSync(outputDir);
    }

    // Extract animation duration and frame count
    const duration = await page.evaluate(() => {
        const svg = document.querySelector('svg');
        return svg.getCurrentTime ? svg.getCurrentTime() : 1; // Default to 5 seconds
    });

    const fps = 30; // Change this for more or fewer frames

    for (let i = 0; i <= fps; i++) {
        // Set SVG time for each frame
        await page.evaluate((time) => {
            const svg = document.querySelector('svg');
            if (svg.setCurrentTime) {
                svg.setCurrentTime(time);
            }
        }, (i / fps) * duration);

        // Take a screenshot of the SVG
        await svgElement.screenshot({ path: path.join(outputDir, `frame_${i}.png`) });
    }

    await browser.close();
}

// Accept URL and output directory from command-line arguments
const url = process.argv[2];
const outputDir = process.argv[3] || 'output';

captureFrames(url, outputDir)
    .then(() => console.log('Frames captured successfully'))
    .catch(err => console.error('Error capturing frames:', err));
