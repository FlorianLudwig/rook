# -*- coding: utf-8 -*-
import sys
import os

for arg in sys.argv:
    dot = 0
    if arg.endswith('.as'):
        dot = 3
    elif arg.endswith('.mxml'):
        dot = 5
    else:
        print 'unknown file', arg
        continue
    name = arg[:-dot]
    if not os.path.exists(arg):
        print arg, 'does not exist'
        continue
    arg_file = os.path.realpath(arg)
    src_path = os.path.join('src'.join(arg_file.split('src')[:-1]), 'src')
    cls_name = arg_file.split('src/')[-1][:-dot].replace('/', '.')
    
    mediator = os.path.join(src_path, 'leijuna', 'view', name + 'Mediator.as')
    context = os.path.join(src_path, 'leijuna', 'LeijunaContext_.as')
    
    # add file and mediator to context
    cont = open(context).read()
    insert_import = '__other_imports__'
    cont = cont.replace(insert_import, insert_import + \
        '\n    import ' + cls_name +
        '\n    import leijuna.view.' + name + 'Mediator.as')
    
    # map view to mediator
    insert_mediators = '__other_mediators__'
    cont = cont.replace(insert_mediators, insert_mediators + \
        '\n            mediatorMap.mapView(' + name + ', ' + name + 'Mediator)')
    open(context, 'w').write(cont) # write context
    
    medi = '''package leijuna.view {
    import ''' + cls_name + '''
    import flash.events.Event
	import org.robotlegs.mvcs.Mediator

	public class ''' + name + '''Mediator extends Mediator {
		[Inject]
		public var view:''' + name + '''

		public override function onRegister():void {
			
		}
	}
}'''
    open(mediator, 'w').write(medi)
    print mediator
