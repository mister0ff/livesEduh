const { WebcastPushConnection } = require('tiktok-live-connector');
const firebase = require('firebase/compat/app');
require('firebase/compat/database');

// Suas credenciais do Firebase
const firebaseConfig = {
  apiKey: "AIzaSyDuKdQkPzGagnCIKUE5Yz_mKtpPw3OCf7c",
  authDomain: "starcord-14470.firebaseapp.com",
  databaseURL: "https://starcord-14470-default-rtdb.firebaseio.com",
  projectId: "starcord-14470",
  storageBucket: "starcord-14470.firebasestorage.app",
  messagingSenderId: "154662528498",
  appId: "1:154662528498:web:ff9815bb21dc2b4172776b",
  measurementId: "G-QR4Y9ZHMF0"
};

firebase.initializeApp(firebaseConfig);
const db = firebase.database();

const tiktokUsername = "eduhh_slk"; 

function connectLive() {
    console.log(`Tentando conectar na live de @${tiktokUsername}...`);
    const tiktokLiveConnection = new WebcastPushConnection(tiktokUsername);

    tiktokLiveConnection.connect().then(state => {
        console.log(`✅ Conectado com sucesso na live da sala: ${state.roomId}`);
    }).catch(err => {
        console.warn('⚠️ Aguardando live... (Se você não estiver ao vivo ou se o TikTok estiver bloqueando, tentaremos novamente em 15 segundos).');
        // Tenta novamente daqui a 15 segundos sem derrubar a aplicação
        setTimeout(connectLive, 15000);
    });

    // Evento disparado quando alguém te SEGUE
    tiktokLiveConnection.on('follow', data => {
        console.log(`Novo seguidor detectado: ${data.uniqueId}`);
        
        // Envia os dados para o Firebase
        db.ref('seguidores/').push({
            nome: data.uniqueId,
            avatar: data.profilePictureUrl
        });
    });

    // Evento caso a live acabe ou caia
    tiktokLiveConnection.on('disconnected', () => {
        console.log('🔄 Live encerrada ou conexão perdida. Tentando reconectar em 15 segundos...');
        setTimeout(connectLive, 15000);
    });
}

// Inicia a primeira tentativa
connectLive();
