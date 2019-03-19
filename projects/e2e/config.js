const fs = require('fs');
const path = require('path');

module.exports = {
  tls: process.env.TLS === 'false' ? false : true,
  listenOptions: {
    host: process.env.LISTEN_OPTIONS_HOST || 'localhost',
    port: parseInt(process.env.LISTEN_OPTIONS_PORT, 10) || 9000
  },
  serverOptions: {
    key: fs.readFileSync(path.resolve(process.env.SERVER_OPTIONS_TLS_KEY_FILE || 'tls/key.pem')),
    cert: fs.readFileSync(path.resolve(process.env.SERVER_OPTIONS_TLS_CERT_FILE || 'tls/cert.pem'))
  },
  wssOptions: {
    path: '/ws',
    serveClient: true,
    pingInterval: 10000,
    pingTimeout: 5000,
    cookie: false
  },
  mediaServerOptions: {
    numWorkers: null,
    rtcIPv4: true,
    rtcIPv6: false,
    rtcAnnouncedIPv4: undefined,
    rtcAnnouncedIPv6: undefined,
    rtcMinPort: undefined,
    rtcMaxPort: undefined
  },
  rtpStreamerOptions: {
    remoteIP: '127.0.0.1'
  },
  mediaCodecs: [
    {
      kind: 'audio',
      name: 'opus',
      clockRate: 48000,
      channels: 2,
      parameters: {
        useinbandfec: 1
      }
    },
    {
      kind: 'video',
      name: 'VP8',
      clockRate: 90000
    },
    {
      kind: 'video',
      name: 'H264',
      clockRate: 90000,
      parameters: {
        'packetization-mode': 1
      }
    }
  ],
  corsOptions: {
    origin: process.env.CORS_OPTIONS_ORIGIN || '*'
  },
  publicDir: path.resolve(process.env.PUBLIC_DIR || 'public'),
  pingInterval: 3000
};
