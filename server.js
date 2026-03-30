const createBackend = require('../shared/create-backend');

createBackend({
  siteName: 'rhythmclaw',
  siteDir: __dirname,
  port: 3003
});
