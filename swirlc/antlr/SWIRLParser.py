# Generated from /swirlc/grammar/SWIRL.g4 by ANTLR 4.13.1
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,16,148,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,1,0,1,0,1,0,5,0,38,8,0,10,0,12,0,41,
        9,0,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,1,2,1,2,1,2,1,2,
        1,2,3,2,59,8,2,1,2,1,2,1,2,5,2,64,8,2,10,2,12,2,67,9,2,1,3,1,3,1,
        3,3,3,72,8,3,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,4,1,5,1,5,1,5,1,5,1,5,
        1,5,1,5,1,5,1,5,1,5,1,6,1,6,1,6,1,6,1,6,1,6,1,6,1,6,1,7,1,7,1,7,
        1,7,1,7,1,7,1,8,1,8,3,8,108,8,8,1,8,1,8,5,8,112,8,8,10,8,12,8,115,
        9,8,1,8,1,8,1,9,1,9,1,9,1,9,1,10,1,10,3,10,125,8,10,1,10,1,10,5,
        10,129,8,10,10,10,12,10,132,9,10,1,10,1,10,1,11,1,11,1,12,1,12,1,
        13,1,13,1,14,1,14,1,15,1,15,1,16,1,16,1,16,0,1,4,17,0,2,4,6,8,10,
        12,14,16,18,20,22,24,26,28,30,32,0,1,1,0,12,14,139,0,34,1,0,0,0,
        2,44,1,0,0,0,4,58,1,0,0,0,6,71,1,0,0,0,8,73,1,0,0,0,10,81,1,0,0,
        0,12,91,1,0,0,0,14,99,1,0,0,0,16,105,1,0,0,0,18,118,1,0,0,0,20,122,
        1,0,0,0,22,135,1,0,0,0,24,137,1,0,0,0,26,139,1,0,0,0,28,141,1,0,
        0,0,30,143,1,0,0,0,32,145,1,0,0,0,34,39,3,2,1,0,35,36,5,13,0,0,36,
        38,3,2,1,0,37,35,1,0,0,0,38,41,1,0,0,0,39,37,1,0,0,0,39,40,1,0,0,
        0,40,42,1,0,0,0,41,39,1,0,0,0,42,43,5,0,0,1,43,1,1,0,0,0,44,45,5,
        1,0,0,45,46,3,26,13,0,46,47,5,2,0,0,47,48,3,16,8,0,48,49,5,2,0,0,
        49,50,3,4,2,0,50,51,5,3,0,0,51,3,1,0,0,0,52,53,6,2,-1,0,53,59,3,
        6,3,0,54,55,5,4,0,0,55,56,3,4,2,0,56,57,5,5,0,0,57,59,1,0,0,0,58,
        52,1,0,0,0,58,54,1,0,0,0,59,65,1,0,0,0,60,61,10,3,0,0,61,62,7,0,
        0,0,62,64,3,4,2,4,63,60,1,0,0,0,64,67,1,0,0,0,65,63,1,0,0,0,65,66,
        1,0,0,0,66,5,1,0,0,0,67,65,1,0,0,0,68,72,3,8,4,0,69,72,3,10,5,0,
        70,72,3,12,6,0,71,68,1,0,0,0,71,69,1,0,0,0,71,70,1,0,0,0,72,7,1,
        0,0,0,73,74,5,6,0,0,74,75,3,32,16,0,75,76,5,2,0,0,76,77,3,18,9,0,
        77,78,5,2,0,0,78,79,3,20,10,0,79,80,5,5,0,0,80,9,1,0,0,0,81,82,5,
        7,0,0,82,83,3,22,11,0,83,84,5,8,0,0,84,85,3,28,14,0,85,86,5,2,0,
        0,86,87,3,30,15,0,87,88,5,2,0,0,88,89,3,24,12,0,89,90,5,5,0,0,90,
        11,1,0,0,0,91,92,5,9,0,0,92,93,3,28,14,0,93,94,5,2,0,0,94,95,3,30,
        15,0,95,96,5,2,0,0,96,97,3,24,12,0,97,98,5,5,0,0,98,13,1,0,0,0,99,
        100,5,4,0,0,100,101,3,28,14,0,101,102,5,2,0,0,102,103,3,22,11,0,
        103,104,5,5,0,0,104,15,1,0,0,0,105,107,5,10,0,0,106,108,3,14,7,0,
        107,106,1,0,0,0,107,108,1,0,0,0,108,113,1,0,0,0,109,110,5,2,0,0,
        110,112,3,14,7,0,111,109,1,0,0,0,112,115,1,0,0,0,113,111,1,0,0,0,
        113,114,1,0,0,0,114,116,1,0,0,0,115,113,1,0,0,0,116,117,5,11,0,0,
        117,17,1,0,0,0,118,119,3,16,8,0,119,120,5,8,0,0,120,121,3,16,8,0,
        121,19,1,0,0,0,122,124,5,10,0,0,123,125,3,26,13,0,124,123,1,0,0,
        0,124,125,1,0,0,0,125,130,1,0,0,0,126,127,5,2,0,0,127,129,3,26,13,
        0,128,126,1,0,0,0,129,132,1,0,0,0,130,128,1,0,0,0,130,131,1,0,0,
        0,131,133,1,0,0,0,132,130,1,0,0,0,133,134,5,11,0,0,134,21,1,0,0,
        0,135,136,5,15,0,0,136,23,1,0,0,0,137,138,5,15,0,0,138,25,1,0,0,
        0,139,140,5,15,0,0,140,27,1,0,0,0,141,142,5,15,0,0,142,29,1,0,0,
        0,143,144,5,15,0,0,144,31,1,0,0,0,145,146,5,15,0,0,146,33,1,0,0,
        0,8,39,58,65,71,107,113,124,130
    ]

class SWIRLParser ( Parser ):

    grammarFileName = "SWIRL.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'<'", "','", "'>'", "'('", "')'", "'exec('", 
                     "'send('", "'->'", "'recv('", "'{'", "'}'", "'+'", 
                     "'|'", "'.'" ]

    symbolicNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "CHOICE", "PAR", "SEQ", "ID", "WS" ]

    RULE_workflow = 0
    RULE_location = 1
    RULE_trace = 2
    RULE_pred = 3
    RULE_exec = 4
    RULE_send = 5
    RULE_recv = 6
    RULE_dataPair = 7
    RULE_dataSet = 8
    RULE_flow = 9
    RULE_mapping = 10
    RULE_data = 11
    RULE_dst = 12
    RULE_name = 13
    RULE_port = 14
    RULE_src = 15
    RULE_step = 16

    ruleNames =  [ "workflow", "location", "trace", "pred", "exec", "send", 
                   "recv", "dataPair", "dataSet", "flow", "mapping", "data", 
                   "dst", "name", "port", "src", "step" ]

    EOF = Token.EOF
    T__0=1
    T__1=2
    T__2=3
    T__3=4
    T__4=5
    T__5=6
    T__6=7
    T__7=8
    T__8=9
    T__9=10
    T__10=11
    CHOICE=12
    PAR=13
    SEQ=14
    ID=15
    WS=16

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.1")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class WorkflowContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def location(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SWIRLParser.LocationContext)
            else:
                return self.getTypedRuleContext(SWIRLParser.LocationContext,i)


        def EOF(self):
            return self.getToken(SWIRLParser.EOF, 0)

        def PAR(self, i:int=None):
            if i is None:
                return self.getTokens(SWIRLParser.PAR)
            else:
                return self.getToken(SWIRLParser.PAR, i)

        def getRuleIndex(self):
            return SWIRLParser.RULE_workflow

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterWorkflow" ):
                listener.enterWorkflow(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitWorkflow" ):
                listener.exitWorkflow(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitWorkflow" ):
                return visitor.visitWorkflow(self)
            else:
                return visitor.visitChildren(self)




    def workflow(self):

        localctx = SWIRLParser.WorkflowContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_workflow)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 34
            self.location()
            self.state = 39
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==13:
                self.state = 35
                self.match(SWIRLParser.PAR)
                self.state = 36
                self.location()
                self.state = 41
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 42
            self.match(SWIRLParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LocationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name(self):
            return self.getTypedRuleContext(SWIRLParser.NameContext,0)


        def dataSet(self):
            return self.getTypedRuleContext(SWIRLParser.DataSetContext,0)


        def trace(self):
            return self.getTypedRuleContext(SWIRLParser.TraceContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_location

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterLocation" ):
                listener.enterLocation(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitLocation" ):
                listener.exitLocation(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLocation" ):
                return visitor.visitLocation(self)
            else:
                return visitor.visitChildren(self)




    def location(self):

        localctx = SWIRLParser.LocationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_location)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 44
            self.match(SWIRLParser.T__0)
            self.state = 45
            self.name()
            self.state = 46
            self.match(SWIRLParser.T__1)
            self.state = 47
            self.dataSet()
            self.state = 48
            self.match(SWIRLParser.T__1)
            self.state = 49
            self.trace(0)
            self.state = 50
            self.match(SWIRLParser.T__2)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TraceContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return SWIRLParser.RULE_trace

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class TraceParenContext(TraceContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SWIRLParser.TraceContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def trace(self):
            return self.getTypedRuleContext(SWIRLParser.TraceContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTraceParen" ):
                listener.enterTraceParen(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTraceParen" ):
                listener.exitTraceParen(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTraceParen" ):
                return visitor.visitTraceParen(self)
            else:
                return visitor.visitChildren(self)


    class TracePredContext(TraceContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SWIRLParser.TraceContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def pred(self):
            return self.getTypedRuleContext(SWIRLParser.PredContext,0)


        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTracePred" ):
                listener.enterTracePred(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTracePred" ):
                listener.exitTracePred(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTracePred" ):
                return visitor.visitTracePred(self)
            else:
                return visitor.visitChildren(self)


    class TraceOpContext(TraceContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a SWIRLParser.TraceContext
            super().__init__(parser)
            self.op = None # Token
            self.copyFrom(ctx)

        def trace(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SWIRLParser.TraceContext)
            else:
                return self.getTypedRuleContext(SWIRLParser.TraceContext,i)

        def CHOICE(self):
            return self.getToken(SWIRLParser.CHOICE, 0)
        def PAR(self):
            return self.getToken(SWIRLParser.PAR, 0)
        def SEQ(self):
            return self.getToken(SWIRLParser.SEQ, 0)

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterTraceOp" ):
                listener.enterTraceOp(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitTraceOp" ):
                listener.exitTraceOp(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTraceOp" ):
                return visitor.visitTraceOp(self)
            else:
                return visitor.visitChildren(self)



    def trace(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = SWIRLParser.TraceContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 4
        self.enterRecursionRule(localctx, 4, self.RULE_trace, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 58
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [6, 7, 9]:
                localctx = SWIRLParser.TracePredContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 53
                self.pred()
                pass
            elif token in [4]:
                localctx = SWIRLParser.TraceParenContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 54
                self.match(SWIRLParser.T__3)
                self.state = 55
                self.trace(0)
                self.state = 56
                self.match(SWIRLParser.T__4)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 65
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,2,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = SWIRLParser.TraceOpContext(self, SWIRLParser.TraceContext(self, _parentctx, _parentState))
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_trace)
                    self.state = 60
                    if not self.precpred(self._ctx, 3):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                    self.state = 61
                    localctx.op = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 28672) != 0)):
                        localctx.op = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 62
                    self.trace(4) 
                self.state = 67
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,2,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class PredContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def exec(self):
            return self.getTypedRuleContext(SWIRLParser.ExecContext,0)


        def send(self):
            return self.getTypedRuleContext(SWIRLParser.SendContext,0)


        def recv(self):
            return self.getTypedRuleContext(SWIRLParser.RecvContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_pred

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPred" ):
                listener.enterPred(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPred" ):
                listener.exitPred(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPred" ):
                return visitor.visitPred(self)
            else:
                return visitor.visitChildren(self)




    def pred(self):

        localctx = SWIRLParser.PredContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_pred)
        try:
            self.state = 71
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [6]:
                self.enterOuterAlt(localctx, 1)
                self.state = 68
                self.exec()
                pass
            elif token in [7]:
                self.enterOuterAlt(localctx, 2)
                self.state = 69
                self.send()
                pass
            elif token in [9]:
                self.enterOuterAlt(localctx, 3)
                self.state = 70
                self.recv()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExecContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def step(self):
            return self.getTypedRuleContext(SWIRLParser.StepContext,0)


        def flow(self):
            return self.getTypedRuleContext(SWIRLParser.FlowContext,0)


        def mapping(self):
            return self.getTypedRuleContext(SWIRLParser.MappingContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_exec

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExec" ):
                listener.enterExec(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExec" ):
                listener.exitExec(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExec" ):
                return visitor.visitExec(self)
            else:
                return visitor.visitChildren(self)




    def exec(self):

        localctx = SWIRLParser.ExecContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_exec)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 73
            self.match(SWIRLParser.T__5)
            self.state = 74
            self.step()
            self.state = 75
            self.match(SWIRLParser.T__1)
            self.state = 76
            self.flow()
            self.state = 77
            self.match(SWIRLParser.T__1)
            self.state = 78
            self.mapping()
            self.state = 79
            self.match(SWIRLParser.T__4)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SendContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def data(self):
            return self.getTypedRuleContext(SWIRLParser.DataContext,0)


        def port(self):
            return self.getTypedRuleContext(SWIRLParser.PortContext,0)


        def src(self):
            return self.getTypedRuleContext(SWIRLParser.SrcContext,0)


        def dst(self):
            return self.getTypedRuleContext(SWIRLParser.DstContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_send

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSend" ):
                listener.enterSend(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSend" ):
                listener.exitSend(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSend" ):
                return visitor.visitSend(self)
            else:
                return visitor.visitChildren(self)




    def send(self):

        localctx = SWIRLParser.SendContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_send)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 81
            self.match(SWIRLParser.T__6)
            self.state = 82
            self.data()
            self.state = 83
            self.match(SWIRLParser.T__7)
            self.state = 84
            self.port()
            self.state = 85
            self.match(SWIRLParser.T__1)
            self.state = 86
            self.src()
            self.state = 87
            self.match(SWIRLParser.T__1)
            self.state = 88
            self.dst()
            self.state = 89
            self.match(SWIRLParser.T__4)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class RecvContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def port(self):
            return self.getTypedRuleContext(SWIRLParser.PortContext,0)


        def src(self):
            return self.getTypedRuleContext(SWIRLParser.SrcContext,0)


        def dst(self):
            return self.getTypedRuleContext(SWIRLParser.DstContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_recv

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterRecv" ):
                listener.enterRecv(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitRecv" ):
                listener.exitRecv(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRecv" ):
                return visitor.visitRecv(self)
            else:
                return visitor.visitChildren(self)




    def recv(self):

        localctx = SWIRLParser.RecvContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_recv)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 91
            self.match(SWIRLParser.T__8)
            self.state = 92
            self.port()
            self.state = 93
            self.match(SWIRLParser.T__1)
            self.state = 94
            self.src()
            self.state = 95
            self.match(SWIRLParser.T__1)
            self.state = 96
            self.dst()
            self.state = 97
            self.match(SWIRLParser.T__4)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DataPairContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def port(self):
            return self.getTypedRuleContext(SWIRLParser.PortContext,0)


        def data(self):
            return self.getTypedRuleContext(SWIRLParser.DataContext,0)


        def getRuleIndex(self):
            return SWIRLParser.RULE_dataPair

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDataPair" ):
                listener.enterDataPair(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDataPair" ):
                listener.exitDataPair(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDataPair" ):
                return visitor.visitDataPair(self)
            else:
                return visitor.visitChildren(self)




    def dataPair(self):

        localctx = SWIRLParser.DataPairContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_dataPair)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 99
            self.match(SWIRLParser.T__3)
            self.state = 100
            self.port()
            self.state = 101
            self.match(SWIRLParser.T__1)
            self.state = 102
            self.data()
            self.state = 103
            self.match(SWIRLParser.T__4)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DataSetContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def dataPair(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SWIRLParser.DataPairContext)
            else:
                return self.getTypedRuleContext(SWIRLParser.DataPairContext,i)


        def getRuleIndex(self):
            return SWIRLParser.RULE_dataSet

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDataSet" ):
                listener.enterDataSet(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDataSet" ):
                listener.exitDataSet(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDataSet" ):
                return visitor.visitDataSet(self)
            else:
                return visitor.visitChildren(self)




    def dataSet(self):

        localctx = SWIRLParser.DataSetContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_dataSet)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 105
            self.match(SWIRLParser.T__9)
            self.state = 107
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==4:
                self.state = 106
                self.dataPair()


            self.state = 113
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==2:
                self.state = 109
                self.match(SWIRLParser.T__1)
                self.state = 110
                self.dataPair()
                self.state = 115
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 116
            self.match(SWIRLParser.T__10)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FlowContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def dataSet(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SWIRLParser.DataSetContext)
            else:
                return self.getTypedRuleContext(SWIRLParser.DataSetContext,i)


        def getRuleIndex(self):
            return SWIRLParser.RULE_flow

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterFlow" ):
                listener.enterFlow(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitFlow" ):
                listener.exitFlow(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFlow" ):
                return visitor.visitFlow(self)
            else:
                return visitor.visitChildren(self)




    def flow(self):

        localctx = SWIRLParser.FlowContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_flow)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 118
            self.dataSet()
            self.state = 119
            self.match(SWIRLParser.T__7)
            self.state = 120
            self.dataSet()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MappingContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def name(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(SWIRLParser.NameContext)
            else:
                return self.getTypedRuleContext(SWIRLParser.NameContext,i)


        def getRuleIndex(self):
            return SWIRLParser.RULE_mapping

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterMapping" ):
                listener.enterMapping(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitMapping" ):
                listener.exitMapping(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMapping" ):
                return visitor.visitMapping(self)
            else:
                return visitor.visitChildren(self)




    def mapping(self):

        localctx = SWIRLParser.MappingContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_mapping)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 122
            self.match(SWIRLParser.T__9)
            self.state = 124
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==15:
                self.state = 123
                self.name()


            self.state = 130
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==2:
                self.state = 126
                self.match(SWIRLParser.T__1)
                self.state = 127
                self.name()
                self.state = 132
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 133
            self.match(SWIRLParser.T__10)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DataContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(SWIRLParser.ID, 0)

        def getRuleIndex(self):
            return SWIRLParser.RULE_data

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterData" ):
                listener.enterData(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitData" ):
                listener.exitData(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitData" ):
                return visitor.visitData(self)
            else:
                return visitor.visitChildren(self)




    def data(self):

        localctx = SWIRLParser.DataContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_data)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 135
            self.match(SWIRLParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DstContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(SWIRLParser.ID, 0)

        def getRuleIndex(self):
            return SWIRLParser.RULE_dst

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterDst" ):
                listener.enterDst(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitDst" ):
                listener.exitDst(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDst" ):
                return visitor.visitDst(self)
            else:
                return visitor.visitChildren(self)




    def dst(self):

        localctx = SWIRLParser.DstContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_dst)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 137
            self.match(SWIRLParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NameContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(SWIRLParser.ID, 0)

        def getRuleIndex(self):
            return SWIRLParser.RULE_name

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterName" ):
                listener.enterName(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitName" ):
                listener.exitName(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitName" ):
                return visitor.visitName(self)
            else:
                return visitor.visitChildren(self)




    def name(self):

        localctx = SWIRLParser.NameContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_name)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 139
            self.match(SWIRLParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PortContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(SWIRLParser.ID, 0)

        def getRuleIndex(self):
            return SWIRLParser.RULE_port

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterPort" ):
                listener.enterPort(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitPort" ):
                listener.exitPort(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPort" ):
                return visitor.visitPort(self)
            else:
                return visitor.visitChildren(self)




    def port(self):

        localctx = SWIRLParser.PortContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_port)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 141
            self.match(SWIRLParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class SrcContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(SWIRLParser.ID, 0)

        def getRuleIndex(self):
            return SWIRLParser.RULE_src

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSrc" ):
                listener.enterSrc(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSrc" ):
                listener.exitSrc(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSrc" ):
                return visitor.visitSrc(self)
            else:
                return visitor.visitChildren(self)




    def src(self):

        localctx = SWIRLParser.SrcContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_src)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 143
            self.match(SWIRLParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StepContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(SWIRLParser.ID, 0)

        def getRuleIndex(self):
            return SWIRLParser.RULE_step

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterStep" ):
                listener.enterStep(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitStep" ):
                listener.exitStep(self)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStep" ):
                return visitor.visitStep(self)
            else:
                return visitor.visitChildren(self)




    def step(self):

        localctx = SWIRLParser.StepContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_step)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 145
            self.match(SWIRLParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx



    def sempred(self, localctx:RuleContext, ruleIndex:int, predIndex:int):
        if self._predicates == None:
            self._predicates = dict()
        self._predicates[2] = self.trace_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def trace_sempred(self, localctx:TraceContext, predIndex:int):
            if predIndex == 0:
                return self.precpred(self._ctx, 3)
         




