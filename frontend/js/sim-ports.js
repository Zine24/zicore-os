/**
 * ZICORE Simulation Ports — WebSocket output ports for VR, display monitors, and remote streaming.
 * Provides real-time entity positions, telemetry, and scene snapshots to connected clients.
 * License: CC BY-NC-SA 4.0
 */
var SimPorts = (function () {
  'use strict';

  var connections = {};
  var wsServer = null;
  var streamInterval = null;
  var getDataFn = null;
  var isStreaming = false;

  function connect(url, portId, callback) {
    if (connections[portId]) {
      if (callback) callback(null, connections[portId]);
      return;
    }

    var ws;
    try {
      ws = new WebSocket(url);
    } catch (e) {
      if (callback) callback(e);
      return;
    }

    ws.onopen = function () {
      connections[portId] = ws;
      ws.send(JSON.stringify({ type: 'register', port: portId }));
      if (callback) callback(null, ws);
    };

    ws.onerror = function (err) {
      if (callback) callback(err);
    };

    ws.onclose = function () {
      delete connections[portId];
    };
  }

  function disconnect(portId) {
    var ws = connections[portId];
    if (ws) {
      ws.close();
      delete connections[portId];
    }
  }

  function disconnectAll() {
    Object.keys(connections).forEach(disconnect);
    connections = {};
  }

  function send(portId, data) {
    var ws = connections[portId];
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
      return true;
    }
    return false;
  }

  function broadcast(data) {
    Object.keys(connections).forEach(function (portId) {
      send(portId, data);
    });
  }

  function startStream(dataFn, intervalMs) {
    getDataFn = dataFn;
    isStreaming = true;
    intervalMs = intervalMs || 50;

    if (streamInterval) clearInterval(streamInterval);
    streamInterval = setInterval(function () {
      if (!isStreaming) return;
      var data = getDataFn ? getDataFn() : null;
      if (data) broadcast(data);
    }, intervalMs);
  }

  function stopStream() {
    isStreaming = false;
    if (streamInterval) {
      clearInterval(streamInterval);
      streamInterval = null;
    }
  }

  function getConnections() {
    return Object.keys(connections)
      .filter(function (k) {
        var ws = connections[k];
        return ws && ws.readyState === WebSocket.OPEN;
      })
      .reduce(function (acc, k) {
        acc[k] = 'connected';
        return acc;
      }, {});
  }

  function sendSnapshot(sceneData) {
    broadcast({
      type: 'scene_snapshot',
      timestamp: Date.now(),
      data: sceneData,
    });
  }

  function sendTelemetry(telemetry) {
    broadcast({
      type: 'telemetry',
      timestamp: Date.now(),
      data: telemetry,
    });
  }

  function sendEntityUpdate(entityData) {
    broadcast({
      type: 'entity_update',
      timestamp: Date.now(),
      data: entityData,
    });
  }

  return {
    connect: connect,
    disconnect: disconnect,
    disconnectAll: disconnectAll,
    send: send,
    broadcast: broadcast,
    startStream: startStream,
    stopStream: stopStream,
    getConnections: getConnections,
    sendSnapshot: sendSnapshot,
    sendTelemetry: sendTelemetry,
    sendEntityUpdate: sendEntityUpdate,
  };
})();
