import java as jj
import com.example as ce


class C(jj.static_proxy(None)):
    @jj.constructor([])
    def __init__(*args):
        pass

    @jj.method(jj.jvoid, [], throws=[ce.Class1])
    def method1(*args):
        pass

    @jj.Override(jj.jfloat, [jj.jboolean])
    @jj.Override(jj.jchar,
                   [jj.jarray(jj.jarray(ce.Class2))])
    def method2(*args):
        pass
