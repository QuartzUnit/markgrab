"""Stealth settings for Playwright to avoid bot detection."""

_STEALTH_SCRIPT = """\
// Remove webdriver flag
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// Realistic languages
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'ko']});

// Mock plugins (Chrome always has these)
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
            {name: 'Native Client', filename: 'internal-nacl-plugin'},
        ];
        plugins.length = 3;
        return plugins;
    }
});

// Mock permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({state: Notification.permission})
        : originalQuery(parameters);

// Chrome runtime mock
window.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}};

// WebGL vendor/renderer (Intel is the most common)
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';           // UNMASKED_VENDOR_WEBGL
    if (parameter === 37446) return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
    return getParameter.call(this, parameter);
};
"""


async def apply_stealth(context) -> None:
    """Apply stealth settings to a Playwright browser context."""
    await context.add_init_script(_STEALTH_SCRIPT)
