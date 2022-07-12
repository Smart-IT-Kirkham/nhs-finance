odoo.define("royal_marsden.view", function (require) {
    "use strict";

    var FormView = require("web.FormController");
    var session = require("web.session");
    var localStorage = require("web.local_storage");
    var ClientIps = [];

    // Override _onButtonClicked method due royalmarsden permission issue of writing in user record. and fraud prevention -
    // header method writing screen details in the user object.

    // Override Update Display method To assign ip address value in global variable "ClientIps"

    FormView.include({
        updateDisplay: function (newAddr) {
            var addrs = Object.create(null);
            addrs["0.0.0.0"] = false;
            if (newAddr in addrs) return;
            addrs[newAddr] = true;
            var displayAddrs = Object.keys(addrs).filter(function (k) {
                return addrs[k];
            });
            ClientIps = displayAddrs.join(" or perhaps ") || "n/a";
            return ClientIps;
        },
        _onButtonClicked: async function (event) {
            event.stopPropagation();
            var self = this;
            var attrs = event.data.attrs;
            var record = event.data.record;
            var clientinfo = window.clientInformation || window.navigator;
            var plugins = [];
            var dnt_res = false;
            var uuid = "";
            var timezone = "";
            if (
                this.modelName === "mtd.hello_world" ||
                this.modelName === "mtd_vat.vat_endpoints"
            ) {
                await this.findIPsWithWebRTC();
                // Client DoNotTrak
                var dnt =
                    typeof navigator.doNotTrack !== "undefined"
                        ? navigator.doNotTrack
                        : typeof window.doNotTrack !== "undefined"
                        ? window.doNotTrack
                        : typeof navigator.msDoNotTrack !== "undefined"
                        ? navigator.msDoNotTrack
                        : null;
                if (parseInt(dnt) === 1 || dnt == "yes") {
                    dnt_res = true;
                }
                // Client Plugins
                for (var i = 0; i < clientinfo.plugins.length; i++) {
                    plugins.push(encodeURIComponent(clientinfo.plugins[i].name));
                }
                // Client ID
                if (
                    localStorage.getItem("clientID") === null ||
                    localStorage.getItem("clientID") === ""
                ) {
                    await new Promise((resolve) => {
                        self._rpc({
                            model: "res.users",
                            method: "get_user_uuid4",
                            args: [[record.context.uid]],
                        }).then(function (res) {
                            uuid = res;
                            resolve(res);
                            localStorage.setItem("clientID", uuid);
                        });
                    });
                } else {
                    uuid = localStorage.getItem("clientID");
                }
                // Client Timezone
                timezone = "UTC" + String(moment().utc().format("Z"));

                var data_dict = {
                    screen_width: screen.width,
                    screen_height: screen.height,
                    screen_depth: screen.colorDepth,
                    screen_scale: window.devicePixelRatio,
                    user_agent: clientinfo.userAgent,
                    browser_plugin:
                        plugins.length !== 0 ? plugins.join(",") : "NoPlugins",
                    browser_dnt: dnt_res,
                    client_ip_address: ClientIps,
                    client_device_id: uuid,
                    client_timezone: timezone,
                };
                self._rpc({
                    model: "res.users",
                    method: "save_screen_details",
                    args: [[session.uid], data_dict],
                }).then(function () {
                    return self
                        .saveRecord(self.handle, {
                            stayInEdit: true,
                        })
                        .then(function () {
                            // We need to reget the record to make sure we have changes made
                            // by the basic model, such as the new res_id, if the record is
                            // new.
                            var current_record = self.model.get(event.data.record.id);
                            return self._callButtonAction(attrs, current_record);
                        });
                });
            } else {
                this._super.apply(this, arguments);
            }
        },
    });
});
