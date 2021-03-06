import os
import sys

import igmconfig
import edrlog
import textwrap

EDRLOG = edrlog.EDRLog()

_thisdir = os.path.abspath(os.path.dirname(__file__))
_overlay_dir = os.path.join(_thisdir, "EDMCOverlay")
if _overlay_dir not in sys.path:
    print "adding {} to sys.path".format(_overlay_dir)
    sys.path.append(_overlay_dir)

try:
    import edmcoverlay
except ImportError:
    print sys.path
    raise Exception(str(sys.path))

import lrucache

class InGameMsg(object):    
    MESSAGE_KINDS = [ "intel", "warning", "sitrep", "notice"]

    def __init__(self):
        self._overlay = edmcoverlay.Overlay()
        self.cfg = {}
        self.body_cache = {}
        self.general_config()
        for kind in self.MESSAGE_KINDS:
            self.message_config(kind)

    def general_config(self):
        conf = igmconfig.IGMConfig()
        self.cfg["general"] = {
            "large" : {
                "h": conf.large_height(),
                "w": conf.large_width()
            },
            "normal" : {
                "h": conf.normal_height(),
                "w": conf.normal_width()
            }
        }


    def message_config(self, kind):
        conf = igmconfig.IGMConfig()
        self.cfg[kind] = {
            "h": {
                "x": conf.x(kind, "header"),
                "y": conf.y(kind, "header"),
                "ttl": conf.ttl(kind, "header"),
                "rgb": conf.rgb(kind, "header"),
                "size": conf.size(kind, "header"),
                "len": conf.len(kind, "header"),
                "align": conf.align(kind, "header")
            },
            "b": {
                "x": conf.x(kind, "body"),
                "y": conf.y(kind, "body"),
                "ttl": conf.ttl(kind, "body"),
                "rgb": conf.rgb(kind, "body"),
                "size": conf.size(kind, "body"),
                "len": conf.len(kind, "body"),
                "align": conf.align(kind, "body"),
                "rows": conf.body_rows(kind),
                "cache": lrucache.LRUCache(conf.body_rows(kind), conf.ttl(kind, "body")),
                "last_row": 0
            }
        }

    def intel(self, header, details):
        self.__msg_header("intel", header)
        self.__msg_body("intel", details)

    def warning(self, header, details):
        self.__msg_header("warning", header)
        self.__msg_body("warning", details)

    def notify(self, header, details):
        self.__msg_header("notice", header)
        self.__msg_body("notice", details)
    
    def sitrep(self, header, details):
        self.__msg_header("sitrep", header)
        self.__msg_body("sitrep", details)

    def __wrap_body(self, kind, lines):
        if not lines:
            return []
        chunked_lines = []
        rows = self.cfg[kind]["b"]["rows"]
        rows_per_line = max(1, rows / len(lines))
        bonus_rows = rows % len(lines)
        for line in lines:
            max_rows = rows_per_line
            if bonus_rows: 
                max_rows += 1
                bonus_rows -= 1
            chunked_lines.append(self.__wrap_text(kind, "b", line, max_rows))
        return chunked_lines

    def __wrap_text(self, kind, part, text, max_rows):
        width = self.cfg[kind][part]["len"]
        wrapper = textwrap.TextWrapper(width=width, subsequent_indent="  ", break_on_hyphens=False)
        return wrapper.wrap(text)[:max_rows]

    def __adjust_x(self, kind, part, text):
        conf = self.cfg[kind][part]
        x = conf["x"]
        if conf["align"] == "center":
            w = self.cfg["general"][conf["size"]]["w"]
            text_w = len(text)*w
            return max(0,int(x-text_w/2.0))
        return x

    def __msg_header(self, kind, header):
        conf = self.cfg[kind]["h"]
        text = header[:conf["len"]]
        x = self.__adjust_x(kind, "h", text)
        print u"header={}, row={}, col={}, color={}, ttl={}, size={}".format(header, conf["y"], x, conf["rgb"], conf["ttl"], conf["size"])
        self.__display(kind, text, row=conf["y"], col=x, color=conf["rgb"], ttl=conf["ttl"], size=conf["size"])

    def __msg_body(self, kind, body):
        conf = self.cfg[kind]["b"]
        x = conf["x"]
        chunked_lines = self.__wrap_body(kind, body)
        
        for chunked_line in chunked_lines:
            for chunk in chunked_line:
                row_nb = self.__best_body_row(kind, chunk)
                y = conf["y"] + row_nb * self.cfg["general"][conf["size"]]["h"]
                conf["cache"].set(row_nb, chunk)
                x = self.__adjust_x(kind, "b", chunk)
                print u"line={}, rownb={}, last_row={}, row={}, col={}, color={}, ttl={}, size={}".format(chunk, row_nb, conf["last_row"], y, x, conf["rgb"], conf["ttl"], conf["size"])
                self.__display(kind, chunk, row=y, col=x, color=conf["rgb"], size=conf["size"], ttl=conf["ttl"])
                self.__bump_body_row(kind)

    def __best_body_row(self, kind, text):
        rows = range(self.cfg[kind]["b"]["rows"])
        used_rows = []
        for row_nb in rows:
            cached = self.cfg[kind]["b"]["cache"].get(row_nb)
            used_rows.append(row_nb)
            if (cached is None or cached == text):
                return row_nb
        
        remaining_rows = (set(rows) - set(used_rows))
        if len(remaining_rows):
            return remaining_rows.pop()
        else:
            self.__bump_body_row(kind)
            return self.cfg[kind]["b"]["last_row"]

    def __bump_body_row(self, kind):
        self.cfg[kind]["b"]["last_row"] += 1
        if self.cfg[kind]["b"]["last_row"] > self.cfg[kind]["b"]["rows"]:
            self.cfg[kind]["b"]["last_row"] = 0


    def __display(self, kind, text, row, col, color="#dd5500", size="large", ttl=5):
        try:
            msgid = "EDR-{}-{}".format(kind, row) 
            self._overlay.send_message(msgid, text, color, int(col), int(row), ttl=ttl, size=size)
        except:
            EDRLOG.log(u"In-Game Message failed.", "ERROR")
            pass

    def shutdown(self):
        # TODO self._overlay.shutdown() or something
        return
