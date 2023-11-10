import datetime, time


TOKEN_SERVER_TIME = new Date().getTime() / 1000


class Base64:
    def __init__(self):
        self.keys = {}
        self.M = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
        for i in range(self.M.length):
            self.keys[self.M[i]] = i

    def base64Encode(self, e):
        f = []
        m = self.M
        i = 0
        while i < len(e):
            d = e[i + 0] << 16 | e[i + 1] << 8 | e[i + 2]
            i += 3
            f.push(m.charAt(d >> 18), m.charAt(d >> 12 & 0x3f), m.charAt(d >> 6 & 0x3f), m.charAt(d & 0x3f))
        f = f.join('')
        return f

    def base64Decode(self, s):
        d = []
        i = 0
        while i < len(s):
            h = self.keys[s.charAt(i + 0)] << 18 | self.keys[s.charAt(i + 1)] << 12 | self.keys[s.charAt(i + 2)] << 6 | self.keys[s.charAt(i + 3)]
            i += 4
            d.push(h >> 16, h >> 8 & 0xff, h & 0xff)
        return d

    # data is Array of length 43
    def encode(self, data):
        e = 0
        for d in data:
            e = (e << 5) - e + d
        r = e & 0xff
        e = [3, r]
        i = 0
        j = 2
        while i < len(data):
            e[j++] = data[i++] ^ r & 0xff;
            r = ~(r * 131);
        // console.log(e);
        f = self.base64Encode(e);
        return f;
    }

    decode(s) {
        t = self.base64Decode(s);
        if (t[0] != 3) {
            // error
            return 0;
        }
        u = t[1];
        rs = [];
        for (j = 2, i = 0; j < t.length; ) {
            rs[i++] = t[j++] ^ u & 0xff;
            u = ~(u * 131);
        }
        console.log(rs);
        // check rs is OK
        e = 0;
        for (i = 0; i < rs.length; i++) {
            e = (e << 5) - e + rs[i];
        }
        e = e & 0xff;
        if (e == t[1]) {
            return rs;
        }
        return 0;
    }


class UserParams {
    constructor() {
        self.mouseMove = 0;
        self.mouseClick = 0;
        self.mouseWhell = 0;
        self.keyDown = 0;
    }

    getMouseMove() {
        self.mouseMove += parseInt(Math.random() * 15);
        return self.mouseMove;
    }
    getMouseClick() {
        self.mouseClick += parseInt(Math.random() * 15);
        return self.mouseClick;
    }
    getMouseWhell() {
        self.mouseWhell += parseInt(Math.random() * 15);
        return self.mouseWhell;
    }
    getKeyDown() {
        self.keyDown += parseInt(Math.random() * 10);
        return self.keyDown;
    }
    getClickPosX() {
        return parseInt(Math.random() * 1024);
    }
    getClickPosY() {
        return parseInt(Math.random() * 720);
    }
    serverTimeNow() {
        diff = self.timeNow() - TOKEN_SERVER_TIME;
        if (diff > 20 * 60) { // 20 minuts
            TOKEN_SERVER_TIME = self.timeNow();
        }
        return parseInt(TOKEN_SERVER_TIME);
    }
    timeNow() {
        return parseInt(Date.now() / 1000);
    }
    ramdom() {
        return parseInt(Math.random() * 4294967295);
    }
}

class Henxin {
    constructor() {
        self.data = [];
        self.base_fileds = [4, 4, 4, 4, 1, 1, 1, 3, 2, 2, 2, 2, 2, 2, 2, 4, 2, 1];
        for (i = 0; i < self.base_fileds.length; i++) {
            self.data[i] = [0];
        }
        self.uiParams = new UserParams();
        self.base64 = new Base64();
    }

    init() {
        self.data[0] = self.uiParams.ramdom();
        self.data[1] = self.uiParams.serverTimeNow();
        self.data[3] = 1486178765; // strhash(navigator.userAgent)
        self.data[4] = 1; // getPlatform
        self.data[5] = 10; // getBrowserIndex
        self.data[6] = 5; // getPluginNum
        self.data[13] = 2724; // getBrowserFeature

        self.data[15] = 0;
        self.data[16] = 0;
        self.data[17] = 3;
    }

    update() {
        self.data[1] = self.uiParams.serverTimeNow();
        self.data[2] = self.uiParams.timeNow();

        self.data[7] = self.uiParams.getMouseMove();
        self.data[8] = self.uiParams.getMouseClick();
        self.data[9] = self.uiParams.getMouseWhell();
        self.data[10] = self.uiParams.getKeyDown();
        self.data[11] = self.uiParams.getClickPosX();
        self.data[12] = self.uiParams.getClickPosY();

        self.data[15] = 0;
        self.data[16]++;

        n = self.toBuffer();
        rs = self.base64.encode(n);
        // console.log('encode:', rs);
        return rs;
    }

    decodeBuffer(buf) {
        r = 0;
        for (bf = self.base_fileds, j = 0, i = 0; i < bf.length; i++) {
            v = bf[i];
            r = 0;
            do {
                r = (r << 8) + buf[j++];
            } while (--v > 0);
            self.data[i] = r >>> 0;
        }
        return r;
    }

    toBuffer() {
        c = [];
        for (s = -1, i = 0, u = self.base_fileds; i < self.base_fileds.length; i++) {
            for (l = self.data[i], p = u[i], d = s += p; c[d] = l & 0xff, --p != 0; ) {
                --d;
                l >>= 8;
            }
        }
        return c;
    }
}

"""
hx = new Henxin();
hx.init();
rs = hx.update();
console.log(rs);
rs = 'http://d.10jqka.com.cn/v6/line/33_002261/01/today.js?hexin-v=' + rs
console.log(rs);

javascript: window.location.href = 'https://s.thsi.cn/js/chameleon/time.1' + (new Date().getTime() / 1200000) + '.js'


"""