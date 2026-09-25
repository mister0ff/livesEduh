const { TikTokLiveConnection, WebcastEvent } = require('tiktok-live-connector');
const firebase = require('firebase/compat/app');
require('firebase/compat/database');

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

const tiktokUsername = "dearjuc";
const connection = new TikTokLiveConnection(tiktokUsername, {});

const curtidasRegistradas = new Set();

function extrairUsuario(data) {
    const nome =
        data.uniqueId ||
        data.user?.uniqueId ||
        data.nickname ||
        data.user?.nickname ||
        null;

    const avatar =
        data.profilePictureUrl ||
        data.user?.profilePicture?.urls?.[0] ||
        data.user?.avatarThumb?.urlList?.[0] ||
        null;

    return { nome, avatar };
}

connection.connect().then(state => {
    console.log(`✅ Conectado com sucesso na live da sala: ${state.roomId}`);
}).catch(err => {
    console.error('❌ Erro ao conectar. Certifique-se de estar ao vivo:', err.message || err);
});

connection.on(WebcastEvent.FOLLOW, data => {
    const { nome, avatar } = extrairUsuario(data);
    if (!nome) { console.log('⚠️ FOLLOW sem nome identificado, dados brutos:', JSON.stringify(data)); return; }
    console.log(`👤 Novo seguidor: ${nome}`);
    db.ref('eventos/').push({ tipo: 'follow', nome, avatar: avatar || null });
});

connection.on(WebcastEvent.LIKE, data => {
    const { nome, avatar } = extrairUsuario(data);
    console.log(`❤️ ${nome || '(sem nome)'} curtiu a live (+${data.likeCount || 1}, total: ${data.totalLikeCount || '?'})`);

    if (!nome) {
        console.log('⚠️ LIKE sem nome identificado, dados brutos:', JSON.stringify(data));
        return;
    }
    if (!curtidasRegistradas.has(nome)) {
        curtidasRegistradas.add(nome);
        db.ref('eventos/').push({ tipo: 'like', nome, avatar: avatar || null });
    }
});

connection.on(WebcastEvent.GIFT, data => {
    if (data.giftType === 1 && !data.repeatEnd) return;
    const { nome, avatar } = extrairUsuario(data);
    if (!nome) { console.log('⚠️ GIFT sem nome identificado, dados brutos:', JSON.stringify(data)); return; }

    const valor = (data.diamondCount || 1) * (data.repeatCount || 1);
    console.log(`🎁 ${nome} enviou ${data.giftName || 'presente'} x${data.repeatCount || 1} (${valor} diamantes)`);

    db.ref('eventos/').push({
        tipo: 'gift', nome, avatar: avatar || null, valor, presente: data.giftName || null
    });
});

// NOVO: Captura o chat e pega apenas a primeira letra
connection.on(WebcastEvent.CHAT, data => {
    const { nome, avatar } = extrairUsuario(data);
    if (!nome) { 
        console.log('⚠️ CHAT sem nome identificado, dados brutos:', JSON.stringify(data)); 
        return; 
    }

    const textoCompleto = data.comment || '';
    const primeiraLetra = textoCompleto.trim().charAt(0); // Pega o primeiro caractere ignorando espaços extras

    if (!primeiraLetra) return; // Se o comentário estiver vazio, ignora

    console.log(`💬 ${nome} comentou ${primeiraLetra}`);

    db.ref('eventos/').push({
        tipo: 'chat',
        nome,
        avatar: avatar || null,
        comentario: primeiraLetra // Salva apenas a primeira letra no Firebase
    });
});

connection.on(WebcastEvent.DISCONNECTED, () => {
    console.log('⚠️ Desconectado da live.');
});

connection.on('error', err => {
    console.error('Erro na conexão:', err);
});
