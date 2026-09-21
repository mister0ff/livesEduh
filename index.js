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

// COLQUE SEU @ DO TIKTOK AQUI (ex: "seu_usuario")
const tiktokUsername = "SEU_USUARIO_DO_TIKTOK"; 
const tiktokLiveConnection = new WebcastPushConnection(tiktokUsername);

tiktokLiveConnection.connect().then(state => {
    console.log(`Conectado com sucesso na live da sala: ${state.roomId}`);
}).catch(err => {
    console.error('Erro ao conectar na live. Certifique-se de estar ao vivo!', err);
});

// Evento disparado quando alguém te SEGUE
tiktokLiveConnection.on('follow', data => {
    console.log(`Novo seguidor: ${data.uniqueId}`);
    
    // Envia os dados para o Firebase
    db.ref('seguidores/').push({
        nome: data.uniqueId,
        avatar: data.profilePictureUrl
    });
});
