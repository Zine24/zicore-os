/* ═══════════════════════════════════════════════════════════════
   ZICORE Browser Polyfills — Universal Compatibility
   Ensures modern APIs work across all browsers
   ═══════════════════════════════════════════════════════════════ */
(function(){
  'use strict';

  /* ── Fetch API polyfill (IE11) ────────────────────────────── */
  if(!window.fetch){
    window.fetch=function(url,opts){
      return new Promise(function(resolve,reject){
        var xhr=new XMLHttpRequest();
        xhr.open(opts&&opts.method||'GET',url);
        if(opts&&opts.headers){
          for(var h in opts.headers)xhr.setRequestHeader(h,opts.headers[h]);
        }
        xhr.onload=function(){
          var headers={};
          xhr.getAllResponseHeaders().split(/\r?\n/).forEach(function(l){
            var p=l.indexOf(':');
            if(p>0)headers[l.slice(0,p).trim().toLowerCase()]=l.slice(p+1).trim();
          });
          resolve({ok:xhr.status>=200&&xhr.status<300,status:xhr.status,statusText:xhr.statusText,headers:{get:function(k){return headers[k.toLowerCase()]}},json:function(){return Promise.resolve(JSON.parse(xhr.responseText))},text:function(){return Promise.resolve(xhr.responseText)},arrayBuffer:function(){return Promise.resolve(xhr.response)}});
        };
        xhr.onerror=function(){reject(new TypeError('Network request failed'))};
        xhr.ontimeout=function(){reject(new TypeError('Network request timeout'))};
        if(opts&&opts.signal){opts.signal.addEventListener('abort',function(){xhr.abort()})}
        xhr.timeout=opts&&opts.timeout||30000;
        xhr.responseType='blob';
        xhr.send(opts&&opts.body||null);
      });
    };
  }

  /* ── Promise polyfill (IE11) ──────────────────────────────── */
  if(typeof Promise==='undefined'){
    window.Promise=function(executor){
      var self=this;
      self._state=0;self._value=undefined;self._callbacks=[];
      function resolve(val){
        if(self._state!==0)return;
        self._state=1;self._value=val;
        self._callbacks.forEach(function(cb){cb.onFulfilled(val)});
      }
      function reject(reason){
        if(self._state!==0)return;
        self._state=2;self._value=reason;
        self._callbacks.forEach(function(cb){cb.onRejected(reason)});
      }
      try{executor(resolve,reject)}catch(e){reject(e)}
    };
    Promise.prototype.then=function(onFulfilled,onRejected){
      var self=this;
      return new Promise(function(resolve,reject){
        function handle(cb){
          setTimeout(function(){
            try{
              var result=cb?cb(self._value):self._value;
              if(result&&typeof result.then==='function')result.then(resolve,reject);
              else resolve(result);
            }catch(e){reject(e)}
          },0);
        }
        if(self._state===1)handle(onFulfilled);
        else if(self._state===2)handle(onRejected);
        else self._callbacks.push({onFulfilled:function(v){handle(onFulfilled)},onRejected:function(r){handle(onRejected)}});
      });
    };
    Promise.prototype['catch']=function(onRejected){return this.then(null,onRejected)};
    Promise.all=function(arr){
      return new Promise(function(resolve,reject){
        var results=[],count=arr.length;
        if(!count)return resolve(results);
        arr.forEach(function(p,i){
          Promise.resolve(p).then(function(v){results[i]=v;if(--count===0)resolve(results)},reject);
        });
      });
    };
    Promise.resolve=function(v){
      if(v instanceof Promise)return v;
      return new Promise(function(r){r(v)});
    };
  }

  /* ── Array.from (IE11) ────────────────────────────────────── */
  if(!Array.from){
    Array.from=function(arr){
      return Array.prototype.slice.call(arr);
    };
  }

  /* ── Array.includes (IE11) ────────────────────────────────── */
  if(!Array.prototype.includes){
    Array.prototype.includes=function(v,i){
      return this.indexOf(v,i!==-1?i:0)!==-1;
    };
  }

  /* ── Object.assign (IE11) ─────────────────────────────────── */
  if(!Object.assign){
    Object.assign=function(target){
      if(target==null)throw new TypeError('Cannot convert undefined or null to object');
      var to=Object(target);
      for(var i=1;i<arguments.length;i++){
        var src=arguments[i];
        if(src!=null)for(var key in src)if(Object.prototype.hasOwnProperty.call(src,key))to[key]=src[key];
      }
      return to;
    };
  }

  /* ── String.startsWith / endsWith / includes (IE11) ───────── */
  if(!String.prototype.startsWith){
    String.prototype.startsWith=function(s,i){return this.indexOf(s,i||0)===0};
  }
  if(!String.prototype.endsWith){
    String.prototype.endsWith=function(s,l){return this.indexOf(s,l===undefined?this.length:l)===s.length};
  }
  if(!String.prototype.includes){
    String.prototype.includes=function(s,i){return this.indexOf(s,i||0)!==-1};
  }
  if(!String.prototype.repeat){
    String.prototype.repeat=function(n){
      var s='',c=String(this);
      while(n-->0)s+=c;
      return s;
    };
  }

  /* ── Element.closest (IE11) ───────────────────────────────── */
  if(!Element.prototype.closest){
    Element.prototype.closest=function(s){
      var el=this;
      while(el&&el!==document){
        if(el.matches(s))return el;
        el=el.parentElement||el.parentNode;
      }
      return null;
    };
  }

  /* ── Element.matches (IE11) ───────────────────────────────── */
  if(!Element.prototype.matches){
    Element.prototype.matches=Element.prototype.msMatchesSelector||Element.prototype.webkitMatchesSelector;
  }

  /* ── CustomEvent (IE11) ───────────────────────────────────── */
  if(typeof CustomEvent!=='function'){
    window.CustomEvent=function(type,opts){
      opts=opts||{bubbles:false,cancelable:false,detail:undefined};
      var e=document.createEvent('CustomEvent');
      e.initCustomEvent(type,opts.bubbles,opts.cancelable,opts.detail);
      return e;
    };
    CustomEvent.prototype=window.Event.prototype;
  }

  /* ── URLSearchParams (IE11) ───────────────────────────────── */
  if(!window.URLSearchParams){
    window.URLSearchParams=function(s){
      this._params={};
      if(s)s.replace(/^\?/,'').split('&').forEach(function(p){
        var kv=p.split('=');
        this._params[decodeURIComponent(kv[0])]=decodeURIComponent(kv.slice(1).join('='));
      }.bind(this));
    };
    URLSearchParams.prototype.get=function(k){return this._params[k]||null};
    URLSearchParams.prototype.set=function(k,v){this._params[k]=v};
    URLSearchParams.prototype.toString=function(){
      return Object.keys(this._params).map(function(k){return encodeURIComponent(k)+'='+encodeURIComponent(this._params[k])}.bind(this)).join('&');
    };
  }

  /* ── CSS Custom Properties fallback (IE11) ────────────────── */
  /* Note: CSS vars can't be polyfilled in JS, but we add a class for CSS fallbacks */
  var cssVarsSupported=(function(){
    try{return window.CSS&&CSS.supports('color','var(--test)')}catch(e){return false}
  })();
  if(!cssVarsSupported)document.documentElement.classList.add('no-css-vars');

  /* ── Flexbox gap (IE11, old Safari) ───────────────────────── */
  (function(){
    var test=document.createElement('div');
    test.style.display='flex';test.style.gap='10px';
    document.body.appendChild(test);
    var hasGap=test.offsetHeight>0&&getComputedStyle(test).gap==='10px';
    document.body.removeChild(test);
    if(!hasGap)document.documentElement.classList.add('no-flex-gap');
  })();

  /* ── IntersectionObserver (IE11) ──────────────────────────── */
  if(!window.IntersectionObserver){
    window.IntersectionObserver=function(callback){
      this._callback=callback;this._elements=[];this._timer=setInterval(this._check.bind(this),200);
    };
    IntersectionObserver.prototype.observe=function(el){this._elements.push(el)};
    IntersectionObserver.prototype.unobserve=function(el){this._elements=this._elements.filter(function(e){return e!==el})};
    IntersectionObserver.prototype.disconnect=function(){clearInterval(this._timer);this._elements=[]};
    IntersectionObserver.prototype._check=function(){
      var self=this;
      this._elements.forEach(function(el){
        var rect=el.getBoundingClientRect();
        var visible=rect.top<window.innerHeight&&rect.bottom>0&&rect.left<window.innerWidth&&rect.right>0;
        self._callback([{target:el,isIntersecting:visible}]);
      });
    };
  }

  /* ── requestAnimationFrame (IE11) ─────────────────────────── */
  if(!window.requestAnimationFrame){
    window.requestAnimationFrame=function(cb){return setTimeout(cb,16)};
    window.cancelAnimationFrame=function(id){clearTimeout(id)};
  }

  /* ── Performance.now (IE11) ───────────────────────────────── */
  if(!window.performance||!window.performance.now){
    window.performance=window.performance||{};
    window.performance.now=function(){return new Date().getTime()};
  }

  /* ── WebRTC Adapter — minimal shim for getUserMedia ──────── */
  if(navigator.mediaDevices&&navigator.mediaDevices.getUserMedia){
    // already supported
  }else if(navigator.webkitGetUserMedia){
    navigator.mediaDevices=navigator.mediaDevices||{};
    navigator.mediaDevices.getUserMedia=function(constraints){
      return new Promise(function(resolve,reject){
        navigator.webkitGetUserMedia(constraints,resolve,reject);
      });
    };
  }else if(navigator.mozGetUserMedia){
    navigator.mediaDevices=navigator.mediaDevices||{};
    navigator.mediaDevices.getUserMedia=function(constraints){
      return new Promise(function(resolve,reject){
        navigator.mozGetUserMedia(constraints,resolve,reject);
      });
    };
  }

  /* ── MediaStream.srcObject (older browsers) ───────────────── */
  var nativeSrcObject=Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype,'srcObject');
  if(!nativeSrcObject||!nativeSrcObject.set){
    Object.defineProperty(HTMLMediaElement.prototype,'srcObject',{
      get:function(){return this._srcObject||null},
      set:function(v){this._srcObject=v;if(v)this.src=URL.createObjectURL(v);else this.src=''},
      configurable:true
    });
  }

  /* ── PointerEvent (IE11) ──────────────────────────────────── */
  if(!window.PointerEvent){
    window.PointerEvent=window.MouseEvent;
    ['pointerdown','pointerup','pointermove','pointerover','pointerout','pointercancel','pointerenter','pointerleave'].forEach(function(type){
      var mouseType=type.replace('pointer','mouse');
      document.addEventListener(type,function(e){
        if(!e.target._peListenerAdded)return;
        var me=new MouseEvent(mouseType,e);
        e.target.dispatchEvent(me);
      },true);
    });
  }

  /* ── CSS Grid support check ───────────────────────────────── */
  (function(){
    var test=document.createElement('div');
    test.style.display='grid';test.style.gridTemplateColumns='1fr 1fr';
    document.body.appendChild(test);
    var supported=test.offsetHeight>0;
    document.body.removeChild(test);
    if(!supported)document.documentElement.classList.add('no-css-grid');
  })();

  /* ── Notification API (IE11) ──────────────────────────────── */
  if(!window.Notification){
    window.Notification={
      permission:'denied',
      requestPermission:function(){return Promise.resolve('denied')},
      function:function(){}
    };
  }

  /* ── Service Worker API (IE11) ────────────────────────────── */
  if(!navigator.serviceWorker){
    navigator.serviceWorker={
      register:function(){return Promise.resolve({unregister:function(){return Promise.resolve(true)}})},
      ready:Promise.resolve(null),
      controller:null
    };
  }

  /* ── WebSocket (IE11 needs polyfill only if blocked) ──────── */
  /* WebSocket is natively supported in IE11 — no polyfill needed */

  /* ── Drag and Drop dataTransfer.files fallback ────────────── */
  /* Most browsers support DnD natively in IE11+ */

  console.log('[ZICORE] Browser polyfills loaded — compatibility layer active');

})();
