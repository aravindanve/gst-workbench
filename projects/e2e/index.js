const http = require('http');
const https = require('https');
const io = require('socket.io');
const express = require('express');
const cors = require('cors');
const mediasoup = require('mediasoup');
const config = require('./config');
const Pipeline = require('./Pipeline');

const app = express()
  .use(cors(config.corsOptions))
  .use(express.static(config.publicDir));

const server = config.tls
  ? https.createServer(config.serverOptions, app)
  : http.createServer(app);

const wss = io(server, config.wssOptions);
const mss = mediasoup.server(config.mssOptions);
const room = mss.Room(config.mediaCodecs);

wss.on('connection', function (socket) {
  socket.joining = false;

  socket.on('request', (payload, ack = NOOP) => {
    switch (payload.method) {
      case 'queryRoom':
        room.receiveRequest(payload)
          .then(data => ack({ data }))
          .catch(error => ack({ error }));
        break;

      case 'join':
        if (socket.joining || room.getPeerByName(socket.id)) {
          ack({ error: 'Peer already joining or joined' });
          break;
        }

        socket.joining = true;
        payload.peerName = socket.id;
        room.receiveRequest(payload)
          .then(response => {
            const peer = room.getPeerByName(socket.id);

            socket.joining = false;

            peer.on('notify', notification =>
              socket.emit('notification', notification));

            peer.on('newproducer', producer =>
              initStreamer(socket, producer));

            peer.on('error', err =>
              console.log('(peer) ERROR', peer.name, err));

            peer.on('close', () => {
              clearStreamers(socket);
              socket.peer = undefined;
            });
            ack({ data: response });
          })
          .catch(error => {
            socket.joining = false;
            ack({ error });
          });
        break;

      default:
        if (!room.getPeerByName(socket.id)) {
          ack({ error: 'Peer not joined' });
          break;
        }

        room.getPeerByName(socket.id).receiveRequest(payload)
          .then(data => ack({ data }))
          .catch(error => ack({ error }));
        break;
    }
  });

  socket.on('notification', (payload, ack = NOOP) => {
    if (!room.getPeerByName(socket.id)) return;
    room.getPeerByName(socket.id).receiveNotification(notification);
    ack();
  });

  socket.on('disconnect', () => {
    const peer = room.getPeerByName(socket.id);

    peer && !peer.closed && peer.close();
    socket.joining = false;
  });
});

function initStreamer(socket, producer) {
  const streamers = socket.streamers = socket.streamers || [];

  

  // getUdpPort((err, port) => {
  //   if (err) {
  //     console.log('(get-udp-port) ERROR', err);
  //     return;
  //   }

  //   getPipeline((err, pipeline) => {
  //     if (err) {
  //       console.log('(get-pipeline) ERROR', err);
  //       return;
  //     }

  //     room.createRtpStreamer(producer, {
  //       ...config.rtpStreamerOptions,
  //       remotePort: port
  //     })
  //     .then(streamer => {
  //       streamer.__port = port;
  //       streamers.push(streamer);

  //       let audioStreamer;
  //       let videoStreamer;

  //       for (let i = 0; i < streamers.length; i++) {
  //         if (audioStreamer && videoStreamer) break;
  //         if (streamers[i].consumer.kind === 'audio') {
  //           audioStreamer = streamers[i];
  //         }
  //         if (streamers[i].consumer.kind === 'video') {
  //           videoStreamer = streamers[i];
  //         }
  //       }

  //       pipeline.createRtpSource({ port }, source => {
  //         // TODO:
  //       });
  //     })
  //     .catch(err => {
  //       console.log('(streamer) ERROR', err);
  //     });
  //   });
  // });
}

function clearStreamers(socket) {

}

const getUdpPort = cb => {
  const socket = createUdpSocket('udp4');

  socket.bind(err => {
    if (err) return cb(err);

    const address = socket.address();

    socket.close();
    setImmediate(cb, null, address.port);
  });
};

wss.on('error', err => console.log('(wss) ERROR', err));
room.on('error', err => console.log('(room) ERROR', err));
server.on('listening', handleHttpListening);

server.listen(config.port, config.host);
