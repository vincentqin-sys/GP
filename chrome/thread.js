function Task(name, delay, exec) {
	// overwrite this function
	this.exec = exec || function (resolve, reject) { };
	this.name = name;
	this.delay = delay || 0;
}

function Thread() {
	this.tasks = [];
	this.id = 0;
	this.curTask = null;
	this.curTaskBeginTime = 0;
}

Thread.prototype.start = function() {
	if (this.id != 0) {
		return;
	}
	let thiz = this;
	function wrapRun() {
		thiz._run();
	}
	this.curTaskBeginTime = Date.now();
	this.id = setInterval(wrapRun, 100);
}

Thread.prototype.pause = function() {
	
}

Thread.prototype._run = function() {
	if (this.curTask != null) {
		return;
	}
	if (this.tasks.length == 0) {
		return;
	}
	let topTask = this.tasks[0];
	let diffTime = Date.now() - this.curTaskBeginTime;
	if (diffTime < topTask.delay) {
		// console.log('Wait...');
		// wait
		return;
	}
	this.curTask = this.tasks.shift();
	let thiz = this;
	function _resolve_() {
		thiz._resolve();
	}
	function _reject_() {
		thiz._reject();
	}
	console.log('Thread.run ', this.curTask);
	this.curTask.exec(this.curTask, _resolve_, _reject_);
}

Thread.prototype._resolve = function() {
	this.curTask = null;
	this.curTaskBeginTime = Date.now();
}

Thread.prototype._reject = function() {
	this.curTask = null;
	this.curTaskBeginTime = Date.now();
	this.tasks.splice(0, this.tasks.length);
}

Thread.prototype.stop = function() {
	clearInterval(this.id);
	this.id = 0;
	this.curTask = null;
	this.curTaskBeginTime = 0;
}

// exec: function(resolve, reject) 
// when finish call resolve() or reject()
Thread.prototype.addTask = function(task) {
	this.tasks.push(task);
}

